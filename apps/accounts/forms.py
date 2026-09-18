"""Formulários Django da app `accounts`."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.utils.translation import gettext_lazy as _


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
    }
