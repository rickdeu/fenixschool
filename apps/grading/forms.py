"""Formulários Django da app `grading`."""

from django import forms
from django.core.exceptions import ValidationError

from apps.core.models import AcademicTerm

from .models import EvaluationType, FinalGrade, Grade
from .services import get_docente_assignments


class GradeAdminForm(forms.ModelForm):
    """Excludes `Grade`'s denormalized fields (`course`/`academic_year`/
    `cycle`/`curricular_year`/`school_class`/`department`) from the form --
    `Grade.save()` derives them automatically from `enrollment`/`subject`,
    so nobody edits them by hand into an inconsistent combination (see the
    model's own docstring).

    Also surfaces RF-AVAL-04's "pauta fechada" block as a normal form error
    (redisplays the form) instead of letting `Grade.save()`'s own
    `GradeReportClosedError` reach the Admin as an unhandled 500 -- that
    model-level check is the real structural guarantee (also holds for any
    future non-Admin caller); this is just a friendlier front door onto it.
    """

    class Meta:
        model = Grade
        fields = [
            "institution",
            "origin_node_id",
            "updated_by",
            "version",
            "is_deleted",
            "student",
            "enrollment",
            "subject",
            "academic_term",
            "evaluation_type",
            "value",
            "teacher",
            "is_grade_report_closed",
        ]

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk and self.instance.is_grade_report_closed:
            raise ValidationError(
                "Esta nota pertence a uma pauta já fechada -- a edição requer autorização."
            )
        return cleaned_data


class FinalGradeAdminForm(forms.ModelForm):
    """`calculated_value`/`overridden_by`/`overridden_at` are deliberately
    left out: `calculated_value` only ever comes from
    `apps.grading.services.registar_media_final`, and `overridden_by`/
    `overridden_at` are set by `FinalGradeAdmin.save_model()` (via
    `apps.grading.services.ajustar_media_manualmente`), never typed in by
    hand.

    Surfaces RF-AVAL-02's "ajuste manual exige justificação" as a normal
    form error, the same friendly-front-door relationship
    `GradeAdminForm.clean()` has for `Grade`'s own closed-pauta check.
    """

    class Meta:
        model = FinalGrade
        fields = [
            "institution",
            "origin_node_id",
            "updated_by",
            "version",
            "is_deleted",
            "enrollment",
            "subject",
            "academic_term",
            "manual_override_value",
            "override_reason",
        ]

    def clean(self):
        cleaned_data = super().clean()
        manual_override_value = cleaned_data.get("manual_override_value")
        override_reason = cleaned_data.get("override_reason")
        if manual_override_value is not None and not (override_reason or "").strip():
            raise ValidationError(
                {
                    "override_reason": (
                        "O ajuste manual da média exige uma justificação (RF-AVAL-02)."
                    )
                }
            )
        return cleaned_data


class GradeGridSelectionForm(forms.Form):
    """Issue #59's first step: pick which turma/disciplina/tipo de
    avaliação/período lectivo to open the grelha de lançamento for.

    `assignment` only ever offers the turma/disciplina pairs `teacher`
    actually teaches (`get_docente_assignments`, via `academic.Schedule`) --
    never every turma/disciplina at the institution, mirroring the same
    object-level scoping enforced again, at the actual point of saving a
    Nota, by `apps.grading.services.lancar_ou_atualizar_nota`.
    """

    assignment = forms.ChoiceField(label="Turma / Disciplina")
    evaluation_type = forms.ModelChoiceField(
        queryset=EvaluationType.objects.none(), label="Tipo de avaliação"
    )
    academic_term = forms.ModelChoiceField(
        queryset=AcademicTerm.objects.none(), label="Período lectivo"
    )

    def __init__(self, *args, teacher, institution, **kwargs):
        super().__init__(*args, **kwargs)
        assignments = get_docente_assignments(teacher)
        self.assignments_by_key = {f"{a.school_class_id}:{a.subject_id}": a for a in assignments}
        self.fields["assignment"].choices = [
            (key, f"{a.school_class} — {a.subject}") for key, a in self.assignments_by_key.items()
        ]
        self.fields["evaluation_type"].queryset = EvaluationType.objects.filter(
            institution=institution
        )
        self.fields["academic_term"].queryset = AcademicTerm.objects.filter(institution=institution)

    def clean_assignment(self):
        key = self.cleaned_data["assignment"]
        if key not in self.assignments_by_key:
            raise ValidationError("Turma/disciplina inválida.")
        return key
