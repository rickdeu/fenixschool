"""Modelo Nota (RF-AVAL-01, docs/05-modelo-de-dados.md §5.17, issue #55)."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import SyncedModel

from .evaluation_type_model import EvaluationType
from .grading_scale_model import GradingScale


class GradeReportClosedError(Exception):
    """RF-AVAL-04: a Nota can't be edited once its pauta is closed (`Grade.
    is_grade_report_closed`), without explicit authorisation. A future
    service (issue #57's `lancar_nota()`/issue #60's reabertura restrita)
    is where that authorisation actually gets checked against the current
    user's permissions -- this is the structural guarantee under it:
    without going through `Grade.save(authorize_closed_edit=True)`
    explicitly, an edit to a closed Nota simply cannot happen, not even by
    accident through the Django Admin or a bug in some other future code
    path.
    """

    def __init__(self, grade):
        self.grade = grade
        super().__init__(
            f'"{grade}" pertence a uma pauta já fechada -- a edição requer autorização.'
        )


class Grade(SyncedModel):
    """ "Nota" -- a single classification for one aluno, in one disciplina,
    for one tipo de avaliação, within the context of one matrícula.

    `course`/`academic_year`/`cycle`/`curricular_year`/`school_class`/
    `department` are **derived**, not chosen by whoever launches the grade:
    a `matrícula` (`enrollment`) already fixes its own course/year/cycle/
    curricular year/turma (see `enrollment.Enrollment`'s own docstring for
    the same reasoning), and `department` comes from the disciplina's own
    curso. `save()` fills them in automatically, matching §5.17's field list
    (which does list them as real columns, for querying/reporting -- e.g. "a
    turma's pauta" -- without a join chain through `enrollment` every time),
    while keeping them impossible to set inconsistently by hand.

    `teacher` ("docente_lancador") is a plain `accounts.User` (profile
    Docente/Diretor de Turma), not the `hr.Funcionario` §5.17 itself
    specifies: `hr.Funcionario` doesn't exist yet (M3) -- same reasoning as
    `academic.Schedule.teacher`.
    """

    student = models.ForeignKey(
        "enrollment.Student", verbose_name="aluno", on_delete=models.PROTECT, related_name="grades"
    )
    enrollment = models.ForeignKey(
        "enrollment.Enrollment",
        verbose_name="matrícula",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    subject = models.ForeignKey(
        "academic.Subject",
        verbose_name="disciplina",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    course = models.ForeignKey(
        "academic.Course", verbose_name="curso", on_delete=models.PROTECT, related_name="grades"
    )
    academic_term = models.ForeignKey(
        "core.AcademicTerm",
        verbose_name="período lectivo",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    academic_year = models.ForeignKey(
        "core.AcademicYear",
        verbose_name="ano lectivo",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    cycle = models.ForeignKey(
        "core.AcademicCycle",
        verbose_name="ciclo lectivo",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    curricular_year = models.ForeignKey(
        "academic.CurricularYear",
        verbose_name="ano curricular",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    school_class = models.ForeignKey(
        "academic.SchoolClass",
        verbose_name="turma",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    department = models.ForeignKey(
        "academic.Department",
        verbose_name="departamento",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    evaluation_type = models.ForeignKey(
        EvaluationType,
        verbose_name="tipo de avaliação",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    value = models.DecimalField(
        "classificação",
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("20"))],
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="docente lançador",
        on_delete=models.PROTECT,
        related_name="grades_launched",
    )
    is_grade_report_closed = models.BooleanField(
        "pauta fechada",
        default=False,
        help_text="RF-AVAL-04: impede edição sem autorização quando activo.",
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "nota"
        verbose_name_plural = "notas"
        # Terminal (non-relation) fields only, never a bare `school_class`/
        # `subject`/`student` -- ordering by a bare FK makes Django expand
        # it into *that* related model's own `Meta.ordering`, recursively,
        # through every FK it in turn orders by (Subject -> Course ->
        # Department/Cycle, CurricularYear -> Course -> ..., etc). With
        # several such FKs on the same model, this exploded into a single
        # changelist query joining `core_institution` 31 times over (260+
        # total joins), hitting SQLite's 64-table join limit outright in
        # tests -- and would still be a needlessly enormous, ever-slower
        # query in production Postgres as the schema grows.
        ordering = [
            "-academic_year__start_date",
            "school_class__designation",
            "subject__name",
            "student__last_name",
            "student__first_name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subject", "academic_term", "evaluation_type"],
                name="grading_grade_unique_per_student_subject_term_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.subject} ({self.evaluation_type}): {self.value}"

    @property
    def qualitative_level(self) -> GradingScale | None:
        """RF-AVAL-03/issue #57: the "nível qualitativo" (e.g. "Bom") that
        corresponds to `value` on the institution's official 0-20 scale
        (issue #56), shown alongside the numeric value wherever a Nota is
        displayed."""
        return GradingScale.for_value(self.value)

    def clean(self):
        errors = {}

        for field_name, label in (
            ("student", "aluno"),
            ("enrollment", "matrícula"),
            ("subject", "disciplina"),
            ("evaluation_type", "tipo de avaliação"),
            ("teacher", "docente"),
        ):
            related = getattr(self, field_name, None)
            institution_id = getattr(related, "institution_id", None)
            if (
                related is not None
                and self.institution_id
                and institution_id
                not in (
                    None,
                    self.institution_id,
                )
            ):
                errors[field_name] = f"O(a) {label} tem de pertencer à mesma instituição."

        if self.enrollment_id and self.student_id and self.enrollment.student_id != self.student_id:
            errors["enrollment"] = "A matrícula tem de pertencer ao mesmo aluno."

        if self.teacher_id:
            from apps.accounts.models import Profile

            if self.teacher.profile not in (Profile.TEACHER, Profile.HOMEROOM_TEACHER):
                errors["teacher"] = "O utilizador escolhido não tem o perfil de Docente."

        if (
            self.subject_id
            and self.enrollment_id
            and self.subject.curricular_year_id != self.enrollment.curricular_year_id
        ):
            errors["subject"] = "A disciplina tem de pertencer ao ano curricular da matrícula."

        if errors:
            raise ValidationError(errors)

    def _derive_denormalized_fields(self):
        self.course_id = self.enrollment.course_id
        self.academic_year_id = self.enrollment.academic_year_id
        self.cycle_id = self.enrollment.cycle_id
        self.curricular_year_id = self.enrollment.curricular_year_id
        self.school_class_id = self.enrollment.school_class_id
        self.department_id = self.subject.course.department_id

    def save(self, *args, authorize_closed_edit=False, **kwargs):
        if self.pk and not authorize_closed_edit:
            current = Grade.all_objects.filter(pk=self.pk).first()
            if current is not None and current.is_grade_report_closed:
                raise GradeReportClosedError(current)

        self._derive_denormalized_fields()
        self.full_clean()
        super().save(*args, **kwargs)
