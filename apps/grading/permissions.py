"""Âmbito de acesso por perfil de utilizador na app `grading`."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.accounts.models import Profile


def docente_required(view_func):
    """Restricts a view to Docente/Diretor de Turma users (issue #59's
    grelha de lançamento de notas) -- same reasoning as
    `guardian_portal.permissions.guardian_required`: Django's own
    `grading.add_grade`/`change_grade` permissions are deliberately *not*
    granted to this profile yet (issue #29's still-open object-level
    scoping half, see `accounts.migrations.0013_grade_permissions`), so
    gating on those would block every Docente outright. The actual
    object-level scoping -- which turma/disciplina this specific docente
    may touch -- is enforced separately, via `academic.Schedule`
    (`apps.grading.services.lancar_ou_atualizar_nota`'s own
    `DocenteNaoAssociadoError` check), not by this profile check alone.
    """

    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.profile not in (Profile.TEACHER, Profile.HOMEROOM_TEACHER):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped_view
