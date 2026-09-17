"""National reference tables (fixtures), pre-loaded from the first installation.

See docs/05-modelo-de-dados.md §5.28 and docs/03-requisitos-nao-funcionais.md
(RNF-LOC-05): provinces/municipalities, mobile operators, identification
document types and professions must ship as system data, not be typed in by
each institution. Deliberately plain `models.Model`, not `SyncedModel`: this is
national reference data shared by every institution, not a per-institution
(tenant-owned) business record -- much like `Institution` itself.

Each model uses a stable, human-readable slug as its primary key (e.g.
"luanda", "huila-lubango") rather than an auto-incrementing id, so that other
apps' models can reference a specific row (e.g. `document_type_id="bi"`)
without depending on fixture load order. See
scripts/generate_core_reference_fixtures.py for how the accompanying fixtures
under `fixtures/` are generated, including a note on the current (post-2024
reform) province/municipality data.
"""

from django.db import models


class Province(models.Model):
    code = models.CharField(max_length=40, primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Municipality(models.Model):
    code = models.CharField(max_length=80, primary_key=True)
    name = models.CharField(max_length=100)
    province = models.ForeignKey(Province, on_delete=models.PROTECT, related_name="municipalities")

    class Meta:
        ordering = ["province__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["province", "name"], name="core_municipality_unique_per_province"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.province.name})"


class MobileOperator(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class IdentificationDocumentType(models.Model):
    # 40, not 20: "bilhete-de-identidade" and "assento-de-nascimento" (see
    # apps/core/fixtures/document_types.json) are 21 characters -- SQLite
    # (used by config.settings.test/base) never enforces CharField length,
    # so this only surfaced against real PostgreSQL (issue #7's local-node
    # stack), when `migrate`'s loaddata step failed loading them.
    code = models.CharField(max_length=40, primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Profession(models.Model):
    code = models.CharField(max_length=60, primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
