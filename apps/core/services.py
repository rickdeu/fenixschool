"""Regras de negócio e transações da app `core`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from datetime import date

from django.db import transaction

from apps.accounts.models import Profile, User

from .context import get_current_node_id, tenant_context
from .models import Institution, NonTeachingDay

# Fixed-date national holidays only (Lei n.º 16/20, de 22 de Maio -- "Lei dos
# Feriados"), as (month, day, description) -- month/day never change year to
# year, unlike the movable ones below. Deliberately NOT included: Carnaval and
# Sexta-Feira Santa, both tied to the date of Easter -- computing/verifying
# those correctly is real, separate work (issue #20's acceptance criterion
# only asks for the initial fixture to pre-load, not a full liturgical
# calendar), so an Administrador da Instituição adds them by hand every year
# via this same screen instead of trusting a silently wrong guess here.
NATIONAL_HOLIDAYS = [
    (1, 1, "Ano Novo"),
    (2, 4, "Dia do Início da Luta Armada de Libertação Nacional"),
    (3, 8, "Dia Internacional da Mulher"),
    (4, 4, "Dia da Paz e Reconciliação Nacional"),
    (5, 1, "Dia Internacional do Trabalhador"),
    (9, 17, "Dia do Herói Nacional"),
    (11, 2, "Dia dos Finados"),
    (11, 11, "Dia da Independência Nacional"),
    (12, 25, "Dia de Natal e da Família"),
]


def seed_national_holidays(institution: Institution, *, origin_node_id, year: int) -> int:
    """Pre-loads the fixed-date national holidays (issue #20's "Feriados
    nacionais pré-carregados" acceptance criterion) for a given calendar
    year. Idempotent -- safe to call again for a year already seeded, e.g.
    from the dedicated screen to cover a future year, since it only adds
    rows for (date, description) pairs that don't already exist.

    Returns how many rows were actually created (0 if this year was already
    fully seeded).
    """
    created = 0
    for month, day, description in NATIONAL_HOLIDAYS:
        _, was_created = NonTeachingDay.objects.get_or_create(
            institution=institution,
            date=date(year, month, day),
            description=description,
            defaults={
                "origin_node_id": origin_node_id,
                "scope": NonTeachingDay.Scope.NATIONAL,
            },
        )
        created += int(was_created)
    return created


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
            origin_node_id = get_current_node_id()
            seed_default_grading_formula(institution, origin_node_id=origin_node_id)
            # Seeds this year and the next: a school year straddles two
            # calendar years (e.g. Feb-Nov), so whichever one the first
            # AcademicYear ends up covering already has its holidays.
            today = date.today()
            seed_national_holidays(institution, origin_node_id=origin_node_id, year=today.year)
            seed_national_holidays(
                institution, origin_node_id=origin_node_id, year=today.year + 1
            )
    return institution, manager
