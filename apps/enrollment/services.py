"""Regras de negócio e transações da app `enrollment`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from django.db import transaction

from apps.reports.services import gerar_comprovativo_matricula_pdf, gerar_declaracao_pdf

from .models import Enrollment, Student

_ACTIVE_ENROLLMENT_STATUSES = {Enrollment.Status.PENDING, Enrollment.Status.ACTIVE}


def get_students_for_guardian(user):
    """§7.2/issue #29: the only Students a Guardian-profile user may ever
    see -- their own linked educandos, never every student at the
    institution. Fails closed (empty queryset) for a user with no linked
    `Guardian` record at all."""
    return Student.objects.for_guardian(user)


def get_enrollments_for_guardian(user):
    """Same restriction as `get_students_for_guardian`, for Matrículas."""
    return Enrollment.objects.for_guardian(user)


class DuplicateStudentDocumentError(Exception):
    """RF-MAT-03: a Student with this identification document is already
    inscribed at this institution -- Inscrição is unique and perpetual."""

    def __init__(self, document_number: str):
        self.document_number = document_number
        super().__init__(
            f'Já existe um aluno inscrito nesta instituição com o documento "{document_number}".'
        )


class SchoolClassFullError(Exception):
    """RF-MAT-07: a SchoolClass already has `max_enrollment` active enrollments.

    A soft (overridable) limit, not a hard block: raised whenever the
    capacity is exceeded and `force=False` (`enroll_student`'s default),
    so the caller (`enrollment_create_view`) can show a warning and ask
    the Secretaria to confirm before enrolling anyway -- issue #174's own
    "aviso, não bloqueio automático" reasoning for `max_enrollment` itself
    extends here too: a class being full is a fact worth surfacing, not a
    reason to refuse a real enrolment decision made by a human."""

    def __init__(self, school_class):
        self.school_class = school_class
        super().__init__(
            f'A turma "{school_class}" atingiu o número máximo de inscritos '
            f"({school_class.max_enrollment})."
        )


class StudentAlreadyEnrolledError(Exception):
    """Um aluno não pode ter mais do que uma matrícula activa (pendente ou
    activa) no mesmo ano lectivo -- ao contrário do tecto de capacidade da
    turma (`SchoolClassFullError`), esta é sempre um bloqueio, nunca
    contornável: duas matrículas activas em simultâneo, no mesmo ano, para
    o mesmo aluno, é sempre um erro de dados, não uma decisão legítima que
    alguém possa querer confirmar na mesma."""

    def __init__(self, student, academic_year, existing_enrollment):
        self.student = student
        self.academic_year = academic_year
        self.existing_enrollment = existing_enrollment
        super().__init__(
            f'"{student}" já tem uma matrícula activa em {academic_year} '
            f'("{existing_enrollment}") -- anule-a ou transfira-a antes de '
            "criar uma nova, em vez de matricular outra vez no mesmo ano."
        )


class MissingGuardianConsentError(Exception):
    """Issue #143, RNF-AUD-02 (Lei 22/11): Inscrição is blocked without a
    Guardian's recorded consent for processing the minor's personal data."""

    def __init__(self):
        super().__init__(
            "A inscrição não pode ser gravada sem o consentimento do Encarregado de "
            "Educação para o tratamento dos dados do aluno."
        )


def register_student(
    *, institution, document_type, document_number, guardian_consent_given_by, **fields
) -> Student:
    """ "Inscrever aluno" (issue #44, RF-MAT-01/03).

    Duplicate-document and missing-consent are both checked explicitly (via
    `all_objects`, independent of the ambient tenant context) *before*
    attempting to create the row, so the caller gets a clear, operator-facing
    exception instead of the database's own `IntegrityError`/`Student.save()`'s
    generic field-required `ValidationError` for what are fundamentally the
    same, expected business rule violations. `all_objects` (not `objects`):
    a soft-deleted student's document must still block a new duplicate
    registration.

    `guardian_consent_given_by` is a required keyword, not folded into
    `**fields`, precisely so a caller can't accidentally omit the consent
    Guardian without an explicit, named argument reminding them it exists
    (issue #143's "Inscrição bloqueada sem consentimento registado").
    """
    if guardian_consent_given_by is None:
        raise MissingGuardianConsentError()

    if Student.all_objects.filter(
        institution=institution, document_type=document_type, document_number=document_number
    ).exists():
        raise DuplicateStudentDocumentError(document_number)

    return Student.objects.create(
        institution=institution,
        document_type=document_type,
        document_number=document_number,
        guardian_consent_given_by=guardian_consent_given_by,
        **fields,
    )


def enroll_student(
    *, institution, student, school_class, force=False, exclude_enrollment_id=None, **fields
) -> Enrollment:
    """ "Matricular aluno" (issue #46, RF-MAT-07).

    Two independent checks, with different consequences on purpose:
    - **Capacidade da turma**: `SchoolClassFullError`, only when `force`
      is falsy -- a warning the Secretaria can confirm past (issue #174's
      own "aviso, não bloqueio automático").
    - **Matrícula duplicada no mesmo ano**: `StudentAlreadyEnrolledError`,
      always -- a student with an already-active enrollment this
      `academic_year` is a data error, never a legitimate override.
      `exclude_enrollment_id` lets `transferir_aluno` create the new
      enrollment without tripping over the very enrollment it is about to
      close.
    """
    academic_year = fields.get("academic_year")
    conflicting_enrollment = (
        Enrollment.objects.filter(
            institution=institution,
            student=student,
            academic_year=academic_year,
            status__in=_ACTIVE_ENROLLMENT_STATUSES,
        )
        .exclude(pk=exclude_enrollment_id)
        .first()
    )
    if conflicting_enrollment is not None:
        raise StudentAlreadyEnrolledError(student, academic_year, conflicting_enrollment)

    if not force and school_class.active_enrollment_count() >= school_class.max_enrollment:
        raise SchoolClassFullError(school_class)

    return Enrollment.objects.create(
        institution=institution,
        student=student,
        school_class=school_class,
        **fields,
    )


# RF-REL-01/issue #94: "3 tipos de declaração geráveis em PDF". Redacção
# genérica de exemplo -- não confirmada junto de nenhum modelo oficial do
# MED -- fica como ponto de partida até a issue #99 construir o ecrã que a
# torna editável por instituição (mesmo raciocínio hedge já usado para
# `Institution.max_recoverable_subjects`/`DEFAULT_EVALUATION_TYPES`).
DECLARACAO_MATRICULA = "declaracao-matricula"
DECLARACAO_FREQUENCIA = "declaracao-frequencia"
DECLARACAO_CONCLUSAO = "declaracao-conclusao"

DECLARACAO_TITLES = {
    DECLARACAO_MATRICULA: "Declaração de Matrícula",
    DECLARACAO_FREQUENCIA: "Declaração de Frequência",
    DECLARACAO_CONCLUSAO: "Declaração de Conclusão",
}

_DEFAULT_DECLARACAO_TEXTS = {
    DECLARACAO_MATRICULA: (
        "Para os devidos efeitos, declara-se que {student} se encontra "
        "matriculado(a) nesta instituição de ensino, na turma {school_class}, "
        "no ano lectivo {academic_year}."
    ),
    DECLARACAO_FREQUENCIA: (
        "Para os devidos efeitos, declara-se que {student} frequenta "
        "actualmente esta instituição de ensino, na turma {school_class}, "
        "no ano lectivo {academic_year}."
    ),
    DECLARACAO_CONCLUSAO: (
        "Para os devidos efeitos, declara-se que {student} concluiu, nesta "
        "instituição de ensino, os estudos correspondentes à turma "
        "{school_class}, no ano lectivo {academic_year}."
    ),
}

# Que estados de `Enrollment.Status` cada tipo de declaração exige --
# "Matrícula" é válida para qualquer matrícula real, seja qual for o seu
# estado actual (é um registo histórico de ter sido matriculado).
_REQUIRED_STATUSES = {
    DECLARACAO_FREQUENCIA: {Enrollment.Status.ACTIVE, Enrollment.Status.PENDING},
    DECLARACAO_CONCLUSAO: {Enrollment.Status.COMPLETED},
}


class TipoDeDeclaracaoIncompativelError(Exception):
    """A matrícula não está num estado compatível com o tipo de declaração
    pedido (ex.: "Declaração de Conclusão" para uma matrícula ainda activa,
    não concluída)."""

    def __init__(self, declaracao_type: str, enrollment: Enrollment):
        self.declaracao_type = declaracao_type
        self.enrollment = enrollment
        super().__init__(
            f'Não é possível emitir "{DECLARACAO_TITLES[declaracao_type]}" para uma '
            f'matrícula com estado "{enrollment.get_status_display()}".'
        )


def emitir_declaracao(*, enrollment: Enrollment, declaracao_type: str, issued_by, origin_node_id):
    """Issue #94 (RF-REL-01): valida que o estado da matrícula é compatível
    com `declaracao_type`, formata o texto legal por omissão e delega a
    numeração/auditoria/renderização a
    `apps.reports.services.gerar_declaracao_pdf` -- que não sabe nada sobre
    `Enrollment`, apenas recebe texto e etiquetas já resolvidos (mesma
    direcção de dependência enrollment/grading → reports, nunca o
    inverso)."""

    required_statuses = _REQUIRED_STATUSES.get(declaracao_type)
    if required_statuses is not None and enrollment.status not in required_statuses:
        raise TipoDeDeclaracaoIncompativelError(declaracao_type, enrollment)

    legal_text = _DEFAULT_DECLARACAO_TEXTS[declaracao_type].format(
        student=enrollment.student,
        school_class=enrollment.school_class.designation,
        academic_year=enrollment.academic_year,
    )

    return gerar_declaracao_pdf(
        institution=enrollment.institution,
        declaracao_type=declaracao_type,
        title=DECLARACAO_TITLES[declaracao_type],
        legal_text=legal_text,
        issued_by=issued_by,
        origin_node_id=origin_node_id,
    )


def emitir_comprovativo_matricula(*, enrollment: Enrollment, issued_by, origin_node_id):
    """Issue #48 (RF-MAT-06): "comprovativo imprimível imediatamente após
    confirmação da matrícula" -- chamado directamente por
    `enrollment_create_view` a seguir a `enroll_student()`, nunca como uma
    acção separada e opcional. Resolve os campos a mostrar e delega a
    numeração/auditoria/renderização a
    `apps.reports.services.gerar_comprovativo_matricula_pdf`."""

    fields = {
        "N.º de matrícula": enrollment.enrollment_number,
        "Aluno": str(enrollment.student),
        "Data de nascimento": enrollment.student.birth_date,
        "Turma": enrollment.school_class.designation,
        "Curso": enrollment.course.name,
        "Ano curricular": enrollment.curricular_year.equivalent_grade,
        "Ano lectivo": str(enrollment.academic_year),
        "Data da matrícula": enrollment.date,
        "Documento apresentado": (
            f"{enrollment.presented_document_type.name} n.º {enrollment.presented_document_number}"
        ),
    }

    return gerar_comprovativo_matricula_pdf(
        institution=enrollment.institution,
        fields=fields,
        issued_by=issued_by,
        origin_node_id=origin_node_id,
    )


class MotivoAnulacaoObrigatorioError(Exception):
    """Issue #51/docs/06-modulos-e-funcionalidades.md §6.4: anular uma
    matrícula exige sempre um motivo preenchido."""

    def __init__(self):
        super().__init__("A anulação de uma matrícula exige um motivo preenchido.")


class MatriculaJaEncerradaError(Exception):
    """Nem `anular_matricula` nem `transferir_aluno` fazem sentido sobre
    uma matrícula que já não está activa (já anulada, transferida ou
    concluída) -- o histórico é imutável a partir daí."""

    def __init__(self, enrollment: Enrollment):
        self.enrollment = enrollment
        super().__init__(
            f'"{enrollment}" já não está activa (estado actual: '
            f'"{enrollment.get_status_display()}").'
        )


def anular_matricula(*, enrollment: Enrollment, reason: str, cancelled_by) -> Enrollment:
    """ "Anular matrícula" (issue #51): muda o estado para Anulada, com
    motivo obrigatório -- nunca elimina o registo (soft-delete/estado), que
    continua consultável no histórico do aluno depois disto."""
    if enrollment.status not in _ACTIVE_ENROLLMENT_STATUSES:
        raise MatriculaJaEncerradaError(enrollment)
    if not reason or not reason.strip():
        raise MotivoAnulacaoObrigatorioError()

    enrollment.status = Enrollment.Status.CANCELLED
    enrollment.cancellation_reason = reason
    enrollment.updated_by = cancelled_by
    enrollment.save()
    return enrollment


def transferir_aluno(
    *, enrollment: Enrollment, school_class, transferred_by, origin_node_id, force=False, **fields
) -> Enrollment:
    """ "Transferir aluno" (issue #49, RF-MAT-08): cria uma nova Matrícula
    em `school_class`, referenciando `enrollment` via `previous_enrollment`
    (histórico preservado), e marca a matrícula antiga como Transferida.

    Só cobre a transferência *dentro da mesma instituição* (mudança de
    turma/curso): "transferência entre instituições da mesma rede transita
    via Nó Central" (o próprio critério de aceitação da issue) depende do
    motor de sincronização entre instituições distintas -- que ainda não
    existe para este fluxo (ver `apps.sync`, hoje só changelog/auditoria de
    sincronização) -- não fabricado aqui à frente dessa dependência real.

    `force` (RF-MAT-08's "limitações configuráveis" na transferência entre
    turmas): repassado a `enroll_student` -- uma turma de destino já cheia
    continua a ser só um aviso, nunca um bloqueio automático (mesmo
    raciocínio de `SchoolClassFullError`).

    A matrícula antiga é fechada (Transferida) *antes* de criar a nova,
    não depois, dentro da mesma transacção -- ao contrário de
    `exclude_enrollment_id` (um simples atalho ao nível do Python),
    `Enrollment.save()` também valida a constraint da base de dados
    (`enrollment_enrollment_one_active_per_student_per_year`), que só vê
    o estado *já gravado* de cada matrícula, não o que `enroll_student`
    pretende excluir. Se `enroll_student` falhar a seguir (capacidade ou
    duplicado), a transacção inteira reverte, incluindo este fecho.
    """
    if enrollment.status not in _ACTIVE_ENROLLMENT_STATUSES:
        raise MatriculaJaEncerradaError(enrollment)

    with transaction.atomic():
        enrollment.status = Enrollment.Status.TRANSFERRED
        enrollment.updated_by = transferred_by
        enrollment.save()

        new_enrollment = enroll_student(
            institution=enrollment.institution,
            student=enrollment.student,
            school_class=school_class,
            origin_node_id=origin_node_id,
            force=force,
            exclude_enrollment_id=enrollment.pk,
            course=school_class.course,
            academic_year=school_class.academic_year,
            cycle=school_class.course.cycle,
            curricular_year=school_class.curricular_year,
            presented_document_type=enrollment.presented_document_type,
            presented_document_number=enrollment.presented_document_number,
            document_issue_date=enrollment.document_issue_date,
            document_issue_place=enrollment.document_issue_place,
            previous_enrollment=enrollment,
            **fields,
        )

    return new_enrollment
