"""Formulários Django da app `accounts`."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField


class LoginForm(AuthenticationForm):
    """Login by email or phone -- no institution field at all (issue #24,
    docs/09-seguranca-e-privacidade.md §9.2). `TenantMiddleware` resolves the
    institution automatically from `request.user` once authenticated.
    """

    username = UsernameField(
        label="Email ou telefone",
        widget=forms.TextInput(attrs={"autofocus": True}),
    )

    error_messages = {
        "invalid_login": (
            "Credenciais inválidas. Verifique o email/telefone e a palavra-passe introduzidos."
        ),
        "inactive": "Esta conta está inactiva. Contacte o Administrador da Instituição.",
    }
