"""The `core.Institution` model — the root tenant of the whole system.

Full data model per docs/05-modelo-de-dados.md §5.2 (issue #15), expanding the
minimal M0 version that existed only to be a valid target for
`SyncedModel.institution`.

One field from §5.2 is deliberately not here yet: `ano_lectivo_corrente`
(`current_academic_year`), a FK to `AnoLectivo`. That model doesn't exist yet —
it's §5.3's `core.AnoLectivo`/`AcademicYear`, built by issue #16 (Models
AnoLectivo, PeriodoLectivo, CicloLectivo e DiaNaoLectivo). Add the FK here once
that model lands, rather than fabricating it against a table that doesn't
exist.
"""

from django.db import models
from uuid6 import uuid7


class Institution(models.Model):
    """A school (the root tenant of the system).

    Does not inherit `SyncedModel`: it *is* the tenant, not a record owned by one,
    so it has no `institution` foreign key of its own.
    """

    # -- Identificação --------------------------------------------------
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=255)
    tax_id = models.CharField("NIF", max_length=50, blank=True, default="")
    ministry_of_education_code = models.CharField(
        "código MED", max_length=50, blank=True, default=""
    )
    description = models.TextField(
        "apresentação",
        blank=True,
        default="",
        help_text=(
            "Apresentação/missão institucional (RF-PUB-01, issue #100) -- mostrada na "
            "página pública, editável por agora via Django Admin até existir uma UI "
            "dedicada (issue #114)."
        ),
    )

    # -- Morada -----------------------------------------------------------
    province = models.ForeignKey(
        "core.Province",
        verbose_name="província",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="institutions",
    )
    municipality = models.ForeignKey(
        "core.Municipality",
        verbose_name="município",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="institutions",
    )
    district_or_commune = models.CharField(
        "distrito/comuna", max_length=100, blank=True, default=""
    )
    neighborhood = models.CharField("bairro", max_length=100, blank=True, default="")
    street = models.CharField("rua", max_length=150, blank=True, default="")
    house_number = models.CharField("número da casa", max_length=20, blank=True, default="")

    # -- Contactos --------------------------------------------------------
    landline_phone = models.CharField("telefone fixo", max_length=20, blank=True, default="")
    unitel_phone = models.CharField("telefone Unitel", max_length=20, blank=True, default="")
    movicel_phone = models.CharField("telefone Movicel", max_length=20, blank=True, default="")
    africell_phone = models.CharField("telefone Africell", max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    website = models.URLField(blank=True, default="")

    # -- Identidade visual --------------------------------------------------
    logo = models.ImageField("logótipo", upload_to="institutions/logos/", blank=True, null=True)

    # -- Parametrização ---------------------------------------------------
    default_grading_formula = models.JSONField(
        "fórmula de média por omissão",
        default=dict,
        blank=True,
        help_text=("Fórmula por omissão de cálculo de médias, sobreponível por curso/disciplina."),
    )
    blocks_documents_with_outstanding_debt = models.BooleanField(
        "bloqueia documentos com dívida",
        default=False,
        help_text="Parametrização financeira (RF-FIN-06).",
    )
    max_recoverable_subjects = models.PositiveSmallIntegerField(
        "máximo de disciplinas em atraso recuperáveis",
        default=2,
        help_text=(
            "RF-AVAL-07/issue #62: acima deste número de disciplinas com média "
            'inferior a 10 valores, a situação final passa de "com disciplinas em '
            'atraso" (RF-AVAL-06\'s avaliação de recurso) a "reprovado". O Anexo '
            "III do RAA (Decreto Executivo 106/26), que fixaria este valor "
            "oficialmente, ainda não foi obtido -- ver "
            'docs/legislacao/escala-avaliacao-secundario.md. "2" é o valor mais '
            "comummente citado em escolas angolanas, não um valor normativo "
            "confirmado -- fica como ponto de partida editável pelo Administrador "
            "da Instituição."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "institution"
        verbose_name_plural = "institutions"

    def __str__(self) -> str:
        return self.name
