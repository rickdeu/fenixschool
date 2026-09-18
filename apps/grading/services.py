"""Regras de negócio e transações da app `grading`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.

RF-INST-06: configuração da fórmula de cálculo de média (pesos de MAC/PT/Exame,
ou quaisquer outros `EvaluationType` que a instituição defina), com sobreposição
opcional por Curso/Disciplina.
"""

from decimal import Decimal

from apps.academic.models import Schedule

from .models import EvaluationType, Grade, GradingFormulaOverride

# Tolerância na soma dos pesos: evita rejeitar `Decimal("0.333") * 3 ==
# Decimal("0.999")` só por causa de arredondamento na representação decimal.
WEIGHT_SUM_TOLERANCE = Decimal("0.01")

# Sugestão inicial genérica (RF-INST-06's próprio exemplo de implementação
# usa estes 3 nomes) para uma instituição recém-criada -- **não é uma fórmula
# confirmada junto do MED**: tentámos verificar os pesos oficiais do Decreto
# Executivo n.º 106/26 (RAA, o regulamento em vigor -- ver
# docs/legislacao/escala-avaliacao-secundario.md) mas a fonte oficial bloqueia
# scraping automático e não localizámos um PDF de texto extraível. Fica como
# ponto de partida editável de imediato pelo Administrador da Instituição, não
# como um valor normativo -- ver docs/implementation-decisions.md.
DEFAULT_EVALUATION_TYPES = (
    ("MAC", Decimal("0.3")),
    ("Prova Trimestral", Decimal("0.3")),
    ("Exame", Decimal("0.4")),
)


class InvalidGradingFormulaError(Exception):
    """A fórmula é vazia, referencia tipos de avaliação inexistentes na
    instituição, ou os pesos indicados não somam 1 (100%)."""


def ensure_default_evaluation_types(institution, *, origin_node_id) -> list[EvaluationType]:
    """Semeia os `EvaluationType` de exemplo do RF-INST-06 para uma instituição
    que ainda não tenha nenhum -- idempotente, para poder ser chamada tanto no
    onboarding (`core.services.setup_institution`) como, para instituições já
    existentes antes desta funcionalidade, lazily a partir da própria view de
    configuração.
    """
    existing_names = set(
        EvaluationType.objects.filter(institution=institution).values_list("name", flat=True)
    )
    for name, weight in DEFAULT_EVALUATION_TYPES:
        if name not in existing_names:
            EvaluationType.objects.create(
                institution=institution,
                name=name,
                default_weight=weight,
                origin_node_id=origin_node_id,
            )
    return list(EvaluationType.objects.filter(institution=institution).order_by("name"))


def validate_formula(formula: dict[str, Decimal], *, institution) -> None:
    """RF-INST-06's acceptance criteria: non-empty, only known evaluation
    types, weights summing to 1 (100%)."""
    if not formula:
        raise InvalidGradingFormulaError("A fórmula não pode ficar vazia.")

    valid_names = set(
        EvaluationType.objects.filter(institution=institution).values_list("name", flat=True)
    )
    unknown = set(formula) - valid_names
    if unknown:
        raise InvalidGradingFormulaError(
            f"Tipo(s) de avaliação desconhecido(s): {', '.join(sorted(unknown))}."
        )

    total = sum(Decimal(str(weight)) for weight in formula.values())
    if abs(total - Decimal("1")) > WEIGHT_SUM_TOLERANCE:
        raise InvalidGradingFormulaError(
            f"A soma dos pesos deve ser 1 (100%) -- soma actual: {total}."
        )


def set_institution_default_formula(institution, formula: dict[str, Decimal]) -> None:
    """Grava a fórmula por omissão da instituição (RF-INST-06)."""
    validate_formula(formula, institution=institution)
    institution.default_grading_formula = {name: str(weight) for name, weight in formula.items()}
    institution.save(update_fields=["default_grading_formula"])


def seed_default_grading_formula(institution, *, origin_node_id) -> None:
    """Called once, from `core.services.setup_institution`, right after a new
    Institution is created -- so it always has a *working* formula from day
    one instead of an empty one blocking every average calculation until an
    Administrator happens to visit the configuration screen (the concern
    behind the "no acto da instalação" request that motivated this).

    Only sets `default_grading_formula` if it's still empty: never overwrites
    a formula an Administrator already customised -- also makes this safe to
    call again (e.g. for an institution created before this function
    existed).
    """
    evaluation_types = ensure_default_evaluation_types(institution, origin_node_id=origin_node_id)
    if not institution.default_grading_formula:
        formula = {
            evaluation_type.name: evaluation_type.default_weight
            for evaluation_type in evaluation_types
        }
        set_institution_default_formula(institution, formula)


def set_course_formula_override(
    course, formula: dict[str, Decimal] | None, *, origin_node_id
) -> None:
    """Grava (ou, com `formula` vazia/`None`, remove) a sobreposição de um Curso."""
    if not formula:
        GradingFormulaOverride.objects.filter(
            institution=course.institution, course=course
        ).delete()
        return

    validate_formula(formula, institution=course.institution)
    weights = {name: str(weight) for name, weight in formula.items()}
    override = GradingFormulaOverride.objects.filter(
        institution=course.institution, course=course
    ).first()
    if override:
        override.weights = weights
        override.save(update_fields=["weights"])
    else:
        GradingFormulaOverride.objects.create(
            institution=course.institution,
            course=course,
            weights=weights,
            origin_node_id=origin_node_id,
        )


def set_subject_formula_override(
    subject, formula: dict[str, Decimal] | None, *, origin_node_id
) -> None:
    """Grava (ou, com `formula` vazia/`None`, remove) a sobreposição de uma Disciplina."""
    if not formula:
        GradingFormulaOverride.objects.filter(
            institution=subject.institution, subject=subject
        ).delete()
        return

    validate_formula(formula, institution=subject.institution)
    weights = {name: str(weight) for name, weight in formula.items()}
    override = GradingFormulaOverride.objects.filter(
        institution=subject.institution, subject=subject
    ).first()
    if override:
        override.weights = weights
        override.save(update_fields=["weights"])
    else:
        GradingFormulaOverride.objects.create(
            institution=subject.institution,
            subject=subject,
            weights=weights,
            origin_node_id=origin_node_id,
        )


def resolve_grading_formula(*, institution, course=None, subject=None) -> dict[str, Decimal]:
    """A Disciplina's own override wins over the Curso's, which wins over the
    Institution's default -- the most specific scope always wins."""
    if subject is not None:
        override = GradingFormulaOverride.objects.filter(
            institution=institution, subject=subject
        ).first()
        if override:
            return {name: Decimal(str(weight)) for name, weight in override.weights.items()}

    if course is not None:
        override = GradingFormulaOverride.objects.filter(
            institution=institution, course=course
        ).first()
        if override:
            return {name: Decimal(str(weight)) for name, weight in override.weights.items()}

    return {
        name: Decimal(str(weight)) for name, weight in institution.default_grading_formula.items()
    }


class NotaForaDaEscalaError(Exception):
    """RF-AVAL-01: a classificação tem de estar entre 0 e 20 (inclusive).

    Checked explicitly here, at the front door of every entry point that
    launches a Nota, instead of relying only on `Grade.value`'s own
    `MinValueValidator`/`MaxValueValidator` -- mirrors the same
    fail-fast-with-a-clear-domain-error pattern already used by
    `enrollment.services`'s `SchoolClassFullError`/`DuplicateStudentDocumentError`.
    """

    def __init__(self, value):
        self.value = value
        super().__init__(f'A classificação "{value}" está fora da escala 0-20.')


class DocenteNaoAssociadoError(Exception):
    """RF-AVAL-01's RBAC acceptance criterion: only the docente actually
    scheduled to teach `subject` in that `school_class` -- via
    `academic.Schedule`, issue #36 -- may launch a Nota for it, not just any
    user with a Docente/Diretor de Turma profile at the institution."""

    def __init__(self, teacher, school_class, subject):
        self.teacher = teacher
        self.school_class = school_class
        self.subject = subject
        super().__init__(
            f'O(a) docente "{teacher}" não lecciona a disciplina "{subject}" '
            f'na turma "{school_class}".'
        )


def lancar_nota(
    *, teacher, enrollment, subject, evaluation_type, academic_term, value, origin_node_id
) -> Grade:
    """ "Lançar nota" (issue #57, RF-AVAL-01/03): validates the 0-20 scale and
    that `teacher` is actually scheduled (`academic.Schedule`) to teach
    `subject` in the enrollment's turma before creating the Nota.

    `student` is deliberately not a parameter: it is always
    `enrollment.student`, the same single source of truth `Grade.clean()`
    itself already enforces -- never something a caller could set
    inconsistently.
    """
    decimal_value = Decimal(str(value))
    if not (Decimal("0") <= decimal_value <= Decimal("20")):
        raise NotaForaDaEscalaError(decimal_value)

    is_associated = Schedule.all_objects.filter(
        institution_id=enrollment.institution_id,
        teacher_id=teacher.id,
        school_class_id=enrollment.school_class_id,
        subject_id=subject.id,
    ).exists()
    if not is_associated:
        raise DocenteNaoAssociadoError(teacher, enrollment.school_class, subject)

    return Grade.objects.create(
        institution=enrollment.institution,
        origin_node_id=origin_node_id,
        student=enrollment.student,
        enrollment=enrollment,
        subject=subject,
        academic_term=academic_term,
        evaluation_type=evaluation_type,
        value=decimal_value,
        teacher=teacher,
    )


def calculate_average(grades: dict[str, Decimal], formula: dict[str, Decimal]) -> Decimal:
    """`calcular_media` (RF-INST-06's exemplo de implementação): weighted sum
    of `grades` (evaluation type name -> classificação) by `formula`
    (evaluation type name -> peso)."""
    missing = set(formula) - set(grades)
    if missing:
        raise ValueError(f"Faltam classificações para: {', '.join(sorted(missing))}.")

    return sum(
        (Decimal(str(grades[name])) * Decimal(str(weight)) for name, weight in formula.items()),
        start=Decimal("0"),
    )
