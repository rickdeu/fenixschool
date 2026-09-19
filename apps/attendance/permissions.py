"""Âmbito de acesso por perfil de utilizador na app `attendance`."""

from apps.accounts.models import Profile
from apps.accounts.permissions import require_profile

# Restricts a view to Docente/Diretor de Turma users (issue #66's registo de
# presença) -- same reasoning as `grading.permissions.docente_required`:
# Django's own `attendance.add_attendance`/`change_attendance` permissions
# are deliberately *not* granted to this profile yet (no object-level
# scoping migration for it either, see `accounts.migrations.
# 0017_attendance_permissions`), so gating on those would block every
# Docente outright. The actual object-level scoping -- which turma/
# disciplina this specific docente may mark attendance for -- is enforced
# separately, via `academic.Schedule`
# (`apps.attendance.services.registar_presencas`'s own
# `DocenteNaoAssociadoError` check), not by this profile check alone.
docente_required = require_profile(Profile.TEACHER, Profile.HOMEROOM_TEACHER)
