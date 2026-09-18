"""Modelo Escala de Avaliação (RF-AVAL-03, issue #56).

See docs/legislacao/escala-avaliacao-secundario.md for the source (Decreto
Executivo 106/26, Anexo II) and docs/implementation-decisions.md for why this
data isn't fabricated ahead of an official text confirmation.
"""

from django.db import models


class GradingScale(models.Model):
    """ "Escala de Avaliação" -- the official 0-20 numeric scale and its 5
    qualitative levels (Excelente..Mau), used to show a qualitative level
    alongside a numeric `Nota` and to determine pass/fail (RF-AVAL-07).

    Deliberately **not** a `SyncedModel`: this is national reference data
    (a legal norm, Decreto Executivo 106/26's Anexo II), identical for every
    institution in Angola -- not a per-institution business record, the same
    reasoning `core.Province`/`core.IdentificationDocumentType`/etc. already
    follow for their own national reference tables. "Editável apenas por
    Super Administrador" (issue #56's acceptance criterion) is enforced via
    RBAC permissions, not by a field on the model itself.
    """

    level = models.PositiveSmallIntegerField("nível", primary_key=True)
    qualitative_level = models.CharField("nível qualitativo", max_length=20, unique=True)
    min_value = models.PositiveSmallIntegerField("valor mínimo")
    max_value = models.PositiveSmallIntegerField("valor máximo")

    class Meta:
        verbose_name = "escala de avaliação"
        verbose_name_plural = "escala de avaliação"
        ordering = ["level"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(min_value__lte=models.F("max_value")),
                name="grading_gradingscale_min_lte_max",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.qualitative_level} ({self.min_value}-{self.max_value})"

    @classmethod
    def for_value(cls, value) -> "GradingScale | None":
        """The qualitative level a given numeric grade (0-20) falls under,
        or `None` if it's outside every configured range (should never
        happen once the official fixture is loaded and `Nota` itself
        validates its own 0-20 range, but this stays a query, not an
        assumption)."""
        return cls.objects.filter(min_value__lte=value, max_value__gte=value).first()
