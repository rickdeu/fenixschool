"""Formulários Django da app `accounts`."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import User


class LoginForm(AuthenticationForm):
    """Login by email or phone -- no institution field at all (issue #24,
    docs/09-seguranca-e-privacidade.md §9.2). `TenantMiddleware` resolves the
    institution automatically from `request.user` once authenticated.

    Labels/messages use `gettext_lazy` (issue #151), not a plain string:
    it defers translation to render time, when `PreferredLanguageMiddleware`
    (issue #149) has already activated the *current request's* language --
    a plain string would instead be translated once, at import time, in
    whatever language happened to be active then.
    """

    username = UsernameField(
        label=_("Email ou telefone"),
        widget=forms.TextInput(attrs={"autofocus": True}),
    )

    error_messages = {
        "invalid_login": _(
            "Credenciais inválidas. Verifique o email/telefone e a palavra-passe introduzidos."
        ),
        "inactive": _("Esta conta está inactiva. Contacte o Administrador da Instituição."),
        "account_locked": _(
            "Esta conta foi temporariamente bloqueada devido a várias tentativas de acesso "
            "falhadas. Tente novamente mais tarde ou contacte o Administrador da Instituição "
            "para a desbloquear de imediato."
        ),
    }

    def clean(self):
        # Checked *before* calling `authenticate()` (issue #26, RNF-SEC-02):
        # a locked account's own backend already rejects it regardless of
        # whether the password is right, which `AuthenticationForm.clean()`
        # would otherwise only ever report as the generic "invalid_login" --
        # not helpful for a legitimate user who mistakes a lockout for a
        # typo. Doesn't itself increment/consume any failed-attempt count.
        username = self.cleaned_data.get("username")
        if username:
            user = User.objects.filter(
                Q(email__iexact=username) | Q(phone=username) | Q(username=username)
            ).first()
            if user is not None and user.is_locked:
                raise forms.ValidationError(
                    self.error_messages["account_locked"], code="account_locked"
                )
        return super().clean()


class TOTPTokenForm(forms.Form):
    """The 6-digit code entry, shared by both 2FA screens (issue #25):
    confirming a brand-new device (setup) and verifying an already-confirmed
    one (every later login). Validation of the code itself (against the
    right `TOTPDevice`) happens in the view, not here -- it needs the
    request's user, which a plain `forms.Form` has no access to.
    """

    token = forms.CharField(
        label=_("Código de verificação"),
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "autofocus": True,
            }
        ),
    )
