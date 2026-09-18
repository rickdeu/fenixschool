"""Regras de negócio e transações da app `core`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from django.db import transaction

from apps.accounts.models import Profile, User

from .context import get_current_node_id, tenant_context
from .models import Institution


def setup_institution(*, institution_data: dict, manager_data: dict) -> tuple[Institution, User]:
    """Onboarding of a new institution (issue #17, docs/04-arquitetura-tecnica.md
    §4.4.2): creates the Institution and its first user (the Manager, profile
    Institution Administrator) in the same transaction, so an institution can
    never end up "orphaned" without one.

    The system's only point where an institution is created for a user with
    no earlier one to inherit from -- doesn't use
    `apps.accounts.services.create_user` (which requires a `created_by`
    already tied to an institution, or a Super Administrator).
    """
    # Local import: avoids `core` (a foundational app every other app already
    # depends on) importing `grading` at module load time -- this is the one
    # place `core` needs to reach into a business app, to seed a working
    # grading formula (issue #18) at institution creation, not module scope.
    from apps.grading.services import seed_default_grading_formula

    with transaction.atomic():
        institution = Institution.objects.create(**institution_data)
        manager = User.objects.create_user(
            institution=institution,
            profile=Profile.INSTITUTION_ADMIN,
            **manager_data,
        )
        with tenant_context(institution.id):
            seed_default_grading_formula(institution, origin_node_id=get_current_node_id())
    return institution, manager
