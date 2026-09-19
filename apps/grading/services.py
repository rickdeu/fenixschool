"""Regras de negócio e transações da app `grading`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.

RF-INST-06: configuração da fórmula de cálculo de média (pesos de MAC/PT/Exame,
ou quaisquer outros `EvaluationType` que a instituição defina), com sobreposição
opcional por Curso/Disciplina.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from apps.academic.models import Schedule, SchoolClass, Subject

from .models import EvaluationType, FinalGrade, FinalSituation, Grade, GradingFormulaOverride

# RF-AVAL-07/docs/legislacao/escala-avaliacao-secundario.md: "Nota mínima de
# aprovação: 10 valores" -- this one *is* officially confirmed (unlike
# `Institution.max_recoverable_subjects`).
PASSING_GRADE = Decimal("10")

# RF-AVAL-06's own exemplo de implementação: "TipoAvaliacao adicional 'Exame
# de Recurso'". Not part of any institution's normal weighted formula
# (`resolve_grading_formula` never references it) -- it only ever resolves
# `calcular_situacao_final`'s pass/fail decision for a disciplina already
# marked "com disciplinas em atraso", never blended into a período's média.
RECURSO_EVALUATION_TYPE_NAME = "Exame de Recurso"

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


def _validate_grade_scale(value) -> Decimal:
    decimal_value = Decimal(str(value))
    if not (Decimal("0") <= decimal_value <= Decimal("20")):
        raise NotaForaDaEscalaError(decimal_value)
    return decimal_value


def _validate_teacher_is_scheduled(*, teacher, enrollment, subject) -> None:
    # "Super Administrador deve ter acesso a tudo, sem restrição alguma" --
    # unlike a real Docente/Diretor de Turma, not tied to any actual
    # Schedule row, so this object-level check would otherwise block them
    # from every turma/disciplina outright.
    if teacher.is_superuser:
        return

    is_associated = Schedule.all_objects.filter(
        institution_id=enrollment.institution_id,
        teacher_id=teacher.id,
        school_class_id=enrollment.school_class_id,
        subject_id=subject.id,
    ).exists()
    if not is_associated:
        raise DocenteNaoAssociadoError(teacher, enrollment.school_class, subject)


class _Assignment:
    """A turma/disciplina pair, shaped just enough like `academic.Schedule`
    (`.school_class`/`.subject`/`.school_class_id`/`.subject_id`) for
    `GradeGridSelectionForm`/`get_docente_assignments`'s own callers to use
    either interchangeably -- used only for a Super Administrador's
    "every turma/disciplina" listing below, which has no real `Schedule`
    row to point at."""

    def __init__(self, school_class, subject):
        self.school_class = school_class
        self.subject = subject
        self.school_class_id = school_class.id
        self.subject_id = subject.id


def get_docente_assignments(teacher) -> list:
    """The turma/disciplina pairs `teacher` may pick from in issue #59's
    grelha de lançamento.

    For a real Docente/Diretor de Turma, only the ones they actually teach
    (`academic.Schedule`, issue #36) -- never any turma/disciplina in the
    institution (the same object-level scoping
    `_validate_teacher_is_scheduled` enforces at the point of actually
    launching a Nota). For a Super Administrador -- "acesso a tudo, sem
    restrição alguma" -- every turma/disciplina combination valid for that
    turma's ano curricular, since they are never actually scheduled to
    teach anything themselves.

    Deduplicated in Python, not via `QuerySet.distinct("field", ...)`: that
    form is Postgres-only, and this project's tests (and some
    local-node deployments) run on SQLite.
    """
    if teacher.is_superuser:
        school_classes = SchoolClass.all_objects.filter(
            institution_id=teacher.institution_id
        ).select_related("curricular_year")
        assignments = [
            _Assignment(school_class, subject)
            for school_class in school_classes
            for subject in Subject.all_objects.filter(
                institution_id=teacher.institution_id,
                curricular_year_id=school_class.curricular_year_id,
            )
        ]
        assignments.sort(key=lambda a: (a.school_class.designation, a.subject.name))
        return assignments

    schedules = (
        Schedule.all_objects.filter(teacher=teacher)
        .select_related("school_class", "subject")
        .order_by("school_class__designation", "subject__name")
    )
    seen = set()
    assignments = []
    for schedule in schedules:
        key = (schedule.school_class_id, schedule.subject_id)
        if key not in seen:
            seen.add(key)
            assignments.append(schedule)
    return assignments


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
    decimal_value = _validate_grade_scale(value)
    _validate_teacher_is_scheduled(teacher=teacher, enrollment=enrollment, subject=subject)

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


def lancar_ou_atualizar_nota(
    *, teacher, enrollment, subject, evaluation_type, academic_term, value, origin_node_id
) -> Grade:
    """Issue #59's grelha de lançamento: unlike `lancar_nota` (issue #57,
    create-only), a docente correcting a value already saved in the grid
    must be able to just resubmit that same cell -- so this updates the
    existing Nota in place when one already exists for this student/
    disciplina/período/tipo de avaliação, instead of hitting `Grade`'s own
    `UniqueConstraint`. Editing an already-closed pauta still goes through
    `Grade.save()`'s own `GradeReportClosedError` -- not silently bypassed
    here.
    """
    decimal_value = _validate_grade_scale(value)
    _validate_teacher_is_scheduled(teacher=teacher, enrollment=enrollment, subject=subject)

    existing = Grade.all_objects.filter(
        institution_id=enrollment.institution_id,
        student=enrollment.student,
        subject=subject,
        academic_term=academic_term,
        evaluation_type=evaluation_type,
    ).first()
    if existing is not None:
        existing.value = decimal_value
        existing.teacher = teacher
        existing.save()
        return existing

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


def atualizar_nota_pauta(*, grade: Grade, value) -> Grade:
    """Correcção de uma nota já lançada, a partir do ecrã de Pautas (issue
    #60) -- ao contrário de `lancar_ou_atualizar_nota`, não exige que quem
    edita seja o docente agendado (é quem gere a homologação -- ex.
    Administrador da Instituição -- a corrigir um valor antes de fechar a
    pauta, não um lançamento pedagógico). O bloqueio de edição depois de
    homologada continua a ser aplicado por `Grade.save()`
    (`GradeReportClosedError`), não é contornado aqui.
    """
    grade.value = _validate_grade_scale(value)
    grade.save()
    return grade


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


class JustificacaoObrigatoriaError(Exception):
    """RF-AVAL-02: um ajuste manual à média final tem sempre de vir
    acompanhado de uma justificação -- sem uma, a auditoria (issue #140)
    registaria *que* alguém mudou o valor, mas nunca *porquê*."""

    def __init__(self):
        super().__init__("O ajuste manual da média exige uma justificação.")


def calcular_media_disciplina(*, enrollment, subject, academic_term) -> Decimal:
    """RF-AVAL-02's exemplo de implementação: reaproveita a fórmula
    parametrizada (`resolve_grading_formula`, RF-INST-06) e as `Nota`s já
    lançadas para esta matrícula/disciplina/período para calcular a média.

    Levanta `ValueError` (de `calculate_average`) se ainda faltar lançar
    alguma nota exigida pela fórmula -- não há média possível sem todas as
    classificações que a fórmula pondera.
    """
    grades = {
        grade.evaluation_type.name: grade.value
        for grade in Grade.objects.filter(
            enrollment=enrollment, subject=subject, academic_term=academic_term
        ).select_related("evaluation_type")
    }
    formula = resolve_grading_formula(
        institution=enrollment.institution, course=enrollment.course, subject=subject
    )
    average = calculate_average(grades, formula)
    # `calculate_average`'s raw Decimal arithmetic keeps every decimal place
    # its inputs happen to produce (a value * a 3-decimal-place peso can
    # already need 4) -- `FinalGrade.calculated_value` only has 2, and
    # Django's `DecimalValidator` counts trailing zeros as real digits, so
    # an unrounded result can overflow `max_digits` outright instead of
    # just losing precision silently.
    return average.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def registar_media_final(*, enrollment, subject, academic_term, origin_node_id) -> FinalGrade:
    """Calcula (`calcular_media_disciplina`) e grava a média -- idempotente e
    recalculável a qualquer momento (ex.: issue #61's avaliação de recurso
    altera uma nota já lançada e a média tem de reflectir isso), sem nunca
    tocar num ajuste manual já registado: só `calculated_value` é
    actualizado, `manual_override_value`/`override_reason` ficam intocados.
    """
    calculated_value = calcular_media_disciplina(
        enrollment=enrollment, subject=subject, academic_term=academic_term
    )

    final_grade = FinalGrade.all_objects.filter(
        institution_id=enrollment.institution_id,
        enrollment=enrollment,
        subject=subject,
        academic_term=academic_term,
    ).first()
    if final_grade is None:
        return FinalGrade.objects.create(
            institution=enrollment.institution,
            origin_node_id=origin_node_id,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            calculated_value=calculated_value,
        )

    final_grade.calculated_value = calculated_value
    final_grade.save()
    return final_grade


def ajustar_media_manualmente(*, final_grade, user, value, reason) -> FinalGrade:
    """RF-AVAL-02's "ajuste manual justificado": overrides a média calculada
    com `value`, exigindo sempre uma `reason` não vazia -- o `clean()` do
    próprio `FinalGrade` é a garantia estrutural por baixo desta, a mesma
    relação que `GradeReportClosedError`/`GradeAdminForm.clean()` já têm
    para `Grade` (issue #55).
    """
    if not reason or not reason.strip():
        raise JustificacaoObrigatoriaError()

    decimal_value = _validate_grade_scale(value)

    final_grade.manual_override_value = decimal_value
    final_grade.override_reason = reason
    final_grade.overridden_by = user
    final_grade.overridden_at = timezone.now()
    final_grade.save()
    return final_grade


class ReaberturaSemJustificacaoError(Exception):
    """RF-AVAL-04/§7.4: reabrir uma pauta já homologada exige sempre uma
    justificação registada -- sem uma, a auditoria (issue #140) saberia
    *que* alguém reabriu, mas nunca *porquê*."""

    def __init__(self):
        super().__init__("A reabertura de uma pauta fechada exige uma justificação.")


def homologar_pauta(grades, *, user) -> int:
    """ "Homologar pauta" (§7.4, RF-AVAL-04): a Direção Pedagógica fecha um
    conjunto de Notas de uma só vez -- a partir daí, cada uma delas só pode
    voltar a ser editada via `reabrir_pauta`.

    `grades` é tipicamente todas as Notas de uma turma/disciplina/tipo de
    avaliação/período (uma "pauta"), mas esta função em si só precisa de um
    iterável de `Grade` -- quem a chama (ex.: uma acção do Django Admin) é
    responsável por escolher o âmbito certo. Notas já fechadas são
    ignoradas (idempotente, não gera um novo "fecho" nem entra outra vez na
    auditoria). Devolve o número de Notas efectivamente fechadas.

    `user.has_perm("grading.change_grade")` -- que só a Direção Pedagógica e
    o Administrador da Instituição têm (`accounts.migrations.
    0013_grade_permissions`) -- é responsabilidade de quem chama verificar
    (ex.: `@permission_required` na view/acção do Admin), não desta função:
    mantém a lógica de RBAC no mesmo sítio onde já vive para todo o resto do
    projecto.
    """
    count = 0
    for grade in grades:
        if grade.is_grade_report_closed:
            continue
        grade.is_grade_report_closed = True
        grade.updated_by = user
        grade.save(authorize_closed_edit=True)
        count += 1
    return count


def reabrir_pauta(grades, *, user, reason) -> int:
    """ "Reabrir pauta" (§7.4, RF-AVAL-04): o inverso de `homologar_pauta`,
    exigindo sempre uma `reason` não vazia. Notas já abertas são ignoradas
    (idempotente). Devolve o número de Notas efectivamente reabertas.
    """
    if not reason or not reason.strip():
        raise ReaberturaSemJustificacaoError()

    count = 0
    for grade in grades:
        if not grade.is_grade_report_closed:
            continue
        grade.is_grade_report_closed = False
        grade.reopening_reason = reason
        grade.updated_by = user
        grade.save(authorize_closed_edit=True)
        count += 1
    return count


def _has_passed_recurso(enrollment, subject) -> bool:
    return Grade.all_objects.filter(
        institution_id=enrollment.institution_id,
        student_id=enrollment.student_id,
        subject=subject,
        evaluation_type__name=RECURSO_EVALUATION_TYPE_NAME,
        value__gte=PASSING_GRADE,
    ).exists()


def calcular_situacao_final(enrollment) -> FinalSituation:
    """ "Calcular situação final" (issue #62, RF-AVAL-07): percorre todas as
    disciplinas do ano curricular da matrícula, calcula a média anual de
    cada uma (a média simples dos `FinalGrade.final_value` já registados
    para essa disciplina -- um por período lectivo com pauta processada;
    uma disciplina sem nenhum ainda não entra na avaliação, não conta como
    reprovada por omissão) e compara com a nota mínima de aprovação (10
    valores, oficialmente confirmada -- ver `PASSING_GRADE`).

    Recalculável a qualquer momento (idempotente via `update_or_create`):
    uma nota de recurso lançada mais tarde (`lancar_nota_recurso`, issue
    #61) só precisa de chamar isto de novo para reflectir-se na situação
    final, sem duplicar a linha.

    `institution.max_recoverable_subjects` -- **não** um valor normativo
    confirmado, ver o próprio campo -- é o que separa "com disciplinas em
    atraso" de "reprovado".
    """
    # `all_objects` (not the tenant-filtered `objects`) throughout: this
    # must work correctly regardless of the ambient tenant context a caller
    # happens to run under -- same reasoning as `_validate_teacher_is_scheduled`.
    subjects = Subject.all_objects.filter(
        institution_id=enrollment.institution_id, curricular_year=enrollment.curricular_year
    )
    failed_subjects = []
    for subject in subjects:
        final_grades = list(
            FinalGrade.all_objects.filter(
                institution_id=enrollment.institution_id, enrollment=enrollment, subject=subject
            ).values_list("manual_override_value", "calculated_value")
        )
        if not final_grades:
            continue
        values = [
            override if override is not None else calculated
            for override, calculated in final_grades
        ]
        annual_average = sum(values) / len(values)
        if annual_average < PASSING_GRADE and not _has_passed_recurso(enrollment, subject):
            failed_subjects.append(subject)

    if not failed_subjects:
        status = FinalSituation.Status.APPROVED
    elif len(failed_subjects) <= enrollment.institution.max_recoverable_subjects:
        status = FinalSituation.Status.PENDING_RECOVERY
    else:
        status = FinalSituation.Status.FAILED

    # `all_objects` (not the tenant-filtered `objects`): mirrors
    # `registar_media_final`'s own reasoning -- this must find an existing
    # row regardless of the ambient tenant context a caller happens to run
    # under.
    situation = FinalSituation.all_objects.filter(
        institution_id=enrollment.institution_id, enrollment=enrollment
    ).first()
    if situation is None:
        situation = FinalSituation.objects.create(
            institution=enrollment.institution,
            origin_node_id=enrollment.origin_node_id,
            enrollment=enrollment,
            status=status,
        )
    else:
        situation.status = status
        situation.save()
    situation.failed_subjects.set(failed_subjects)
    return situation


class DisciplinaNaoEstaEmRecursoError(Exception):
    """RF-AVAL-06: uma avaliação de recurso só faz sentido para uma
    disciplina que a matrícula já reprovou (consta em
    `FinalSituation.failed_subjects`) -- nunca uma que já passou."""

    def __init__(self, subject):
        self.subject = subject
        super().__init__(f'"{subject}" não está em situação de recurso para esta matrícula.')


def lancar_nota_recurso(
    *, enrollment, subject, value, teacher, academic_term, origin_node_id
) -> Grade:
    """ "Lançar nota de recurso" (issue #61, RF-AVAL-06): registra a
    classificação obtida no exame de recurso/recuperação de uma disciplina
    já reprovada, e recalcula de imediato a situação final da matrícula
    (`calcular_situacao_final`) para reflectir a resolução.

    Só é aceite para uma disciplina que a matrícula já reprova
    (`DisciplinaNaoEstaEmRecursoError` caso contrário) -- a própria
    `calcular_situacao_final` é quem decide, ao recalcular, se este valor
    (>= 10 valores) resolve ou não a pendência (`_has_passed_recurso`); esta
    função só regista a Nota, nunca decide a situação final directamente.

    Idempotente por (aluno, disciplina, período, "Exame de Recurso"): uma
    segunda chamada actualiza a mesma Nota em vez de colidir com a
    `UniqueConstraint` de `Grade`.
    """
    situation = FinalSituation.all_objects.filter(
        institution_id=enrollment.institution_id, enrollment=enrollment
    ).first()
    if situation is None or not situation.failed_subjects.filter(pk=subject.pk).exists():
        raise DisciplinaNaoEstaEmRecursoError(subject)

    decimal_value = _validate_grade_scale(value)
    evaluation_type = ensure_recurso_evaluation_type(
        enrollment.institution, origin_node_id=origin_node_id
    )

    existing = Grade.all_objects.filter(
        institution_id=enrollment.institution_id,
        student_id=enrollment.student_id,
        subject=subject,
        academic_term=academic_term,
        evaluation_type=evaluation_type,
    ).first()
    if existing is not None:
        existing.value = decimal_value
        existing.teacher = teacher
        existing.save()
        grade = existing
    else:
        grade = Grade.objects.create(
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

    calcular_situacao_final(enrollment)
    return grade


def ensure_recurso_evaluation_type(institution, *, origin_node_id) -> EvaluationType:
    """Get-or-create the institution's "Exame de Recurso" `EvaluationType`
    (RF-AVAL-06's own exemplo de implementação) -- created lazily, on first
    actual use, not seeded upfront for every institution like
    `DEFAULT_EVALUATION_TYPES` (issue #18): most disciplinas most períodos
    never need one."""
    evaluation_type, _created = EvaluationType.objects.get_or_create(
        institution=institution,
        name=RECURSO_EVALUATION_TYPE_NAME,
        defaults={"default_weight": Decimal("0"), "origin_node_id": origin_node_id},
    )
    return evaluation_type


def get_boletim_rows(*, institution, enrollment, academic_term) -> list[dict]:
    """Issue #97 (RF-REL-04): uma linha por disciplina com `FinalGrade` já
    calculada para `enrollment`/`academic_term`, com as respectivas notas
    por tipo de avaliação -- usado tanto pelo ecrã (`boletim_view`) como
    pela exportação em PDF (`boletim_pdf_view`), para que ambos mostrem
    exactamente os mesmos dados."""
    final_grades = (
        FinalGrade.objects.filter(
            institution=institution, enrollment=enrollment, academic_term=academic_term
        )
        .select_related("subject")
        .order_by("subject__name")
    )
    rows = []
    for final_grade in final_grades:
        grades = (
            Grade.objects.filter(
                institution=institution,
                enrollment=enrollment,
                subject=final_grade.subject,
                academic_term=academic_term,
            )
            .select_related("evaluation_type")
            .order_by("evaluation_type__name")
        )
        rows.append({"final_grade": final_grade, "grades": grades})
    return rows
