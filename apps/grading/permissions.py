"""Âmbito de acesso por perfil de utilizador na app `grading`."""

from apps.accounts.models import Profile
from apps.accounts.permissions import require_profile

# Restricts a view to Docente/Diretor de Turma users (issue #59's grelha de
# lançamento de notas) -- same reasoning as
# `guardian_portal.permissions.guardian_required`: Django's own
# `grading.add_grade`/`change_grade` permissions are deliberately *not*
# granted to this profile yet (issue #29's still-open object-level scoping
# half, see `accounts.migrations.0013_grade_permissions`), so gating on
# those would block every Docente outright. The actual object-level scoping
# -- which turma/disciplina this specific docente may touch -- is enforced
# separately, via `academic.Schedule`
# (`apps.grading.services.lancar_ou_atualizar_nota`'s own
# `DocenteNaoAssociadoError` check), not by this profile check alone.
#
# `require_profile` already lets a Super Administrador through regardless
# of profile -- their own Schedule-based grid will simply show no
# assignments (no turma is naturally "theirs" to teach), but they are never
# blocked outright, matching "acesso a tudo, sem restrição alguma".
docente_required = require_profile(Profile.TEACHER, Profile.HOMEROOM_TEACHER)
