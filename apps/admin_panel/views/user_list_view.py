"""Lista de utilizadores da instituição (issue #113, RF-ADM-01)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from apps.accounts.models import User
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("accounts.view_user", raise_exception=True)
def user_list_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    # Explicit `institution=` filter, not `User.objects.all()`: `User`
    # isn't a `SyncedModel` (its `institution` is nullable, for Super
    # Administrador), so there's no automatic tenant filtering here --
    # without this, an Administrador da Instituição would see every
    # institution's staff.
    users = User.objects.filter(institution=request.institution).order_by(
        "last_name", "first_name"
    )

    return render(request, "admin_panel/user_list.html", {"users": users})
