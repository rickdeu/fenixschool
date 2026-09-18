"""Formulários Django da app `admin_panel`."""

from decimal import Decimal

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.accounts.services import ASSIGNABLE_PROFILES_FOR_INSTITUTION_ADMIN
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


class UserCreateForm(forms.Form):
    """Novo utilizador (issue #113, RF-ADM-01) -- `profile` está sempre
    limitado a `ASSIGNABLE_PROFILES_FOR_INSTITUTION_ADMIN`: um Administrador
    da Instituição nunca pode, através deste ecrã, criar um Super
    Administrador (âmbito de rede, não desta instituição)."""

    username = forms.CharField(label=_("Nome de utilizador"), max_length=150)
    first_name = forms.CharField(label=_("Nome"), max_length=150, required=False)
    last_name = forms.CharField(label=_("Sobrenome"), max_length=150, required=False)
    email = forms.EmailField(label=_("Email"), required=False)
    phone = forms.CharField(label=_("Telefone"), max_length=20, required=False)
    profile = forms.ChoiceField(
        label=_("Perfil"), choices=ASSIGNABLE_PROFILES_FOR_INSTITUTION_ADMIN
    )
    password = forms.CharField(label=_("Palavra-passe"), widget=forms.PasswordInput)
    password_confirmation = forms.CharField(
        label=_("Confirmar palavra-passe"), widget=forms.PasswordInput
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError(_("Já existe um utilizador com este nome."))
        return username

    def clean_password(self):
        # RNF-SEC-02/issue #26's own password policy (AUTH_PASSWORD_VALIDATORS)
        # applies here too -- a colleague's account created through this
        # screen is no less subject to it than a self-registered one.
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirmation = cleaned_data.get("password_confirmation")
        if password and password_confirmation and password != password_confirmation:
            self.add_error("password_confirmation", _("As palavras-passe não coincidem."))
        return cleaned_data


class UserEditForm(forms.Form):
    """Edição de utilizador (issue #113) -- `institution` nunca aparece
    aqui: é definida uma única vez na criação e nunca editada através de um
    formulário comum (docs/04-arquitetura-tecnica.md §4.4.1)."""

    first_name = forms.CharField(label=_("Nome"), max_length=150, required=False)
    last_name = forms.CharField(label=_("Sobrenome"), max_length=150, required=False)
    email = forms.EmailField(label=_("Email"), required=False)
    phone = forms.CharField(label=_("Telefone"), max_length=20, required=False)
    profile = forms.ChoiceField(
        label=_("Perfil"), choices=ASSIGNABLE_PROFILES_FOR_INSTITUTION_ADMIN
    )
    is_active = forms.BooleanField(label=_("Conta activa"), required=False)
