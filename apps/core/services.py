"""Regras de negócio e transações da app `core`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

import os
import subprocess
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Profile, User

from .context import get_current_node_id, tenant_context
from .models import Institution, NonTeachingDay

# Fixed-date national holidays (Lei n.º 10/11, de 16 de Fevereiro -- "Regime
# Jurídico dos Feriados Nacionais e Locais e Datas de Celebração Nacional",
# alterada pela Lei n.º 11/18, de 28 de Setembro), as (month, day,
# description) -- month/day never change year to year, unlike the movable
# ones below.
NATIONAL_HOLIDAYS = [
    (1, 1, "Ano Novo"),
    (2, 4, "Dia do Início da Luta Armada de Libertação Nacional"),
    (3, 8, "Dia Internacional da Mulher"),
    (3, 23, "Dia da Libertação da África Austral"),
    (4, 4, "Dia da Paz e Reconciliação Nacional"),
    (5, 1, "Dia Internacional do Trabalhador"),
    (9, 17, "Dia do Herói Nacional"),
    (11, 2, "Dia dos Finados"),
    (11, 11, "Dia da Independência Nacional"),
    (12, 25, "Dia de Natal e da Família"),
]


def _easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm (Computus) -- computes Easter Sunday for
    any Gregorian-calendar year without a network call or a third-party
    dependency, so the movable holidays below stay correct offline, on any
    Nó Local, for any year (verified against 2024-03-31/2025-04-20/2026-04-05/
    2027-03-28, the well-known Easter dates for those years).
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day_of_month = ((h + ell - 7 * m + 114) % 31) + 1
    return date(year, month, day_of_month)


def _movable_holidays(year: int) -> list[tuple[date, str]]:
    """Carnaval and Sexta-Feira Santa (Lei n.º 10/11) -- both fixed relative to
    Easter Sunday, not to the calendar, so they can't be listed in
    `NATIONAL_HOLIDAYS` alongside the fixed-date ones above."""
    easter = _easter_sunday(year)
    return [
        (easter - timedelta(days=47), "Carnaval"),
        (easter - timedelta(days=2), "Sexta-Feira Santa"),
    ]


def seed_national_holidays(institution: Institution, *, origin_node_id, year: int) -> int:
    """Pre-loads every national holiday, fixed-date and movable alike (issue
    #20's "Feriados nacionais pré-carregados" acceptance criterion), for a
    given calendar year -- nothing here is ever left for an Administrador da
    Instituição to type in by hand. Idempotent -- safe to call again for a
    year already seeded, e.g. from the dedicated screen to (re)cover a given
    year on demand, since it only adds rows for (date, description) pairs
    that don't already exist.

    Returns how many rows were actually created (0 if this year was already
    fully seeded).
    """
    all_holidays = [
        (date(year, month, day), description) for month, day, description in NATIONAL_HOLIDAYS
    ]
    all_holidays += _movable_holidays(year)

    created = 0
    for holiday_date, description in all_holidays:
        _, was_created = NonTeachingDay.objects.get_or_create(
            institution=institution,
            date=holiday_date,
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
    # depends on) importing `grading`/`sync` at module load time -- this is
    # the one place `core` needs to reach into another app, to seed a
    # working grading formula (issue #18) and this node's own sync identity
    # (issue #123) at installation, not module scope.
    from apps.grading.services import seed_default_grading_formula
    from apps.sync.services import create_local_node

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
            seed_national_holidays(institution, origin_node_id=origin_node_id, year=today.year + 1)

    # Fora da transacção acima de propósito: gera um ficheiro no disco (a
    # chave privada do Node), que uma reversão da transacção da Instituição/
    # Gestor não desfaria -- ver `create_local_node()`.
    create_local_node(institution=institution)

    return institution, manager


def backup_database() -> Path:
    """A logical (`pg_dump`) backup of the local node's own database (issue
    #166's "backup automático" acceptance criterion, docs/11-implantacao-e-
    operacoes.md §11.4), gzipped to `BACKUP_DIR` (defaults to `/app/backups`,
    the volume every service in docker-compose.local-node.yml already shares).

    Runs automatically once a day via Django-Q2
    (`apps.core.signals.schedule_automatic_backup`), and can also be invoked
    by hand: `python manage.py backup_database`.

    Same approach as `scripts/backup.sh` (a plain dump before gzip, never a
    piped `pg_dump | gzip`, so a failing `pg_dump` can't produce a corrupt-
    but-"successful"-looking `.sql.gz`) -- but connects over the network
    (`--host`) rather than running inside the `db` container itself, since
    this runs from `web`/`qcluster`, a separate container that only has the
    `pg_dump` client installed, not the server.
    """
    db = settings.DATABASES["default"]
    backup_dir = Path(os.environ.get("BACKUP_DIR", "/app/backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
    dump_path = backup_dir / f"fenixschool-{timestamp}.sql"

    subprocess.run(
        [
            "pg_dump",
            "--host",
            db["HOST"],
            "--port",
            str(db["PORT"] or 5432),
            "--username",
            db["USER"],
            "--dbname",
            db["NAME"],
            "--file",
            str(dump_path),
        ],
        env={**os.environ, "PGPASSWORD": db["PASSWORD"]},
        check=True,
    )
    subprocess.run(["gzip", "--force", str(dump_path)], check=True)
    return dump_path.with_name(dump_path.name + ".gz")
