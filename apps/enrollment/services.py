"""Regras de negócio e transações da app `enrollment`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from apps.reports.services import gerar_declaracao_pdf

from .models import Enrollment, Student


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
    """RF-MAT-07: a SchoolClass already has `max_enrollment` active enrollments."""

    def __init__(self, school_class):
        self.school_class = school_class
        super().__init__(
            f'A turma "{school_class}" atingiu o número máximo de inscritos '
            f"({school_class.max_enrollment})."
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


def enroll_student(*, institution, student, school_class, **fields) -> Enrollment:
    """ "Matricular aluno" (issue #46, RF-MAT-07): blocks enrollment once a
    class's `max_enrollment` active enrollments are already taken."""
    if school_class.active_enrollment_count() >= school_class.max_enrollment:
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
