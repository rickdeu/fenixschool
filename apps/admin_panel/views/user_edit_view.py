"""Edição de utilizador (issue #113, RF-ADM-01)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import User

from ..forms import UserEditForm
from .grading_formula_config_view import require_institution_context


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def user_edit_view(request, user_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    # `institution=request.institution`: an Administrador da Instituição
    # can only ever reach their *own* institution's staff through this
    # screen -- a Super Administrador (network-wide) is never a match here,
    # since their own `institution` is always `None`.
    target_user = get_object_or_404(User, pk=user_id, institution=request.institution)

    if request.method == "POST":
        form = UserEditForm(request.POST)
        if form.is_valid():
            for field, value in form.cleaned_data.items():
                setattr(target_user, field, value)
            target_user.save()
            success(request, f'Utilizador "{target_user}" actualizado.')
            return redirect("admin_panel:user_list")
    else:
        form = UserEditForm(
            initial={
                "first_name": target_user.first_name,
                "last_name": target_user.last_name,
                "email": target_user.email,
                "phone": target_user.phone,
                "profile": target_user.profile,
                "is_active": target_user.is_active,
            }
        )

    return render(
        request,
        "admin_panel/user_form.html",
        {"form": form, "is_create": False, "target_user": target_user},
    )
