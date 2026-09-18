"""Regras de negócio e transações da app `grading`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.

RF-INST-06: configuração da fórmula de cálculo de média (pesos de MAC/PT/Exame,
ou quaisquer outros `EvaluationType` que a instituição defina), com sobreposição
opcional por Curso/Disciplina.
"""

from decimal import Decimal

from .models import EvaluationType, GradingFormulaOverride

# Tolerância na soma dos pesos: evita rejeitar `Decimal("0.333") * 3 ==
# Decimal("0.999")` só por causa de arredondamento na representação decimal.
WEIGHT_SUM_TOLERANCE = Decimal("0.01")

# Sugestão inicial (RF-INST-06's exemplo de implementação) para uma instituição
# recém-criada -- editável de imediato pelo seu Administrador, nunca aplicada
# como fórmula activa sem confirmação (`Institution.default_grading_formula`
# só é preenchido quando o Administrador gravar o formulário).
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
    institution.default_grading_formula = {
        name: str(weight) for name, weight in formula.items()
    }
    institution.save(update_fields=["default_grading_formula"])


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
        name: Decimal(str(weight))
        for name, weight in institution.default_grading_formula.items()
    }


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
