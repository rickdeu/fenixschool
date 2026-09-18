"""Âmbito de acesso por perfil de utilizador na app `guardian_portal`."""

from apps.accounts.models import Profile
from apps.accounts.permissions import require_profile

# Restricts a view to authenticated Encarregado de Educação users
# (issue #52) -- distinct from gating by the coarser
# `enrollment.view_student` Django permission (issue #29), which several
# staff profiles also hold for their own, unrelated admin-side visibility
# into student records.
#
# `require_profile` already lets a Super Administrador through regardless
# of profile (see its own docstring) -- their dashboard will simply show no
# educandos (they aren't a real Guardian for anyone), but they are never
# blocked outright.
guardian_required = require_profile(Profile.GUARDIAN)
