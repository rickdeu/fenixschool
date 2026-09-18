"""Formulários Django da app `admin_panel`."""

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from apps.grading.models import EvaluationType
from apps.grading.services import InvalidGradingFormulaError, validate_formula


class GradingFormulaForm(forms.Form):
    """Edição dos pesos de MAC/PT/Exame (ou quaisquer outros
    `EvaluationType` da instituição) na fórmula de média (RF-INST-06, issue
    #18) -- um campo de peso por tipo de avaliação, dinamicamente construído
    a partir dos `EvaluationType` já existentes na instituição.
    """

    def __init__(self, *args, institution, initial_formula=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.institution = institution
        self.evaluation_types = list(
            EvaluationType.objects.filter(institution=institution).order_by("name")
        )
        initial_formula = initial_formula or {}
        for evaluation_type in self.evaluation_types:
            self.fields[self._field_name(evaluation_type)] = forms.DecimalField(
                label=evaluation_type.name,
                required=False,
                min_value=Decimal("0"),
                max_value=Decimal("1"),
                max_digits=4,
                decimal_places=3,
                initial=initial_formula.get(
                    evaluation_type.name, evaluation_type.default_weight
                ),
                help_text="Peso na fórmula (0 a 1) -- em branco para não usar este tipo.",
            )

    @staticmethod
    def _field_name(evaluation_type: EvaluationType) -> str:
        return f"weight_{evaluation_type.id}"

    def clean(self):
        cleaned_data = super().clean()
        self.formula = {
            evaluation_type.name: cleaned_data[self._field_name(evaluation_type)]
            for evaluation_type in self.evaluation_types
            if cleaned_data.get(self._field_name(evaluation_type)) is not None
        }
        try:
            validate_formula(self.formula, institution=self.institution)
        except InvalidGradingFormulaError as error:
            raise ValidationError(str(error)) from error
        return cleaned_data
