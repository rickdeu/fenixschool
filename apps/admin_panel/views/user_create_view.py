"""Criação de utilizador (issue #113, RF-ADM-01)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.shortcuts import redirect, render

from apps.accounts.services import create_user

from ..forms import UserCreateForm
from .grading_formula_config_view import require_institution_context


@login_required
@permission_required("accounts.add_user", raise_exception=True)
def user_create_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            fields = dict(form.cleaned_data)
            fields.pop("password_confirmation")
            # `institution=request.institution`: covers a Super
            # Administrador using this screen too (they have no
            # `institution` of their own -- `create_user()` requires one
            # explicitly in that case). For every other creator, the
            # service ignores this and uses `created_by.institution`
            # instead, per its own docstring.
            user = create_user(created_by=request.user, institution=request.institution, **fields)
            success(request, f'Utilizador "{user}" criado.')
            return redirect("admin_panel:user_list")
    else:
        form = UserCreateForm()

    return render(request, "admin_panel/user_form.html", {"form": form, "is_create": True})
