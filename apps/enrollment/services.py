"""Regras de negócio e transações da app `enrollment`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from .models import Enrollment, Student


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


def register_student(*, institution, document_type, document_number, **fields) -> Student:
    """ "Inscrever aluno" (issue #44, RF-MAT-01/03).

    Checked explicitly (via `all_objects`, independent of the ambient tenant
    context) *before* attempting to create the row, so the caller gets
    `DuplicateStudentDocumentError` -- a clear, operator-facing message --
    instead of the database's own `IntegrityError`/`Student.save()`'s
    `ValidationError` for what is fundamentally the same, expected business
    rule violation. `all_objects` (not `objects`): a soft-deleted student's
    document must still block a new duplicate registration.
    """
    if Student.all_objects.filter(
        institution=institution, document_type=document_type, document_number=document_number
    ).exists():
        raise DuplicateStudentDocumentError(document_number)

    return Student.objects.create(
        institution=institution,
        document_type=document_type,
        document_number=document_number,
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
