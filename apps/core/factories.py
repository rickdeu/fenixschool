"""`factory_boy` factories for `core`'s models — see docs/13-testes-e-qualidade.md §13.1.

Used both directly by this app's own tests and, via the shared fixtures in the
repository's root `conftest.py`, by every other app's tests.
"""

import factory
from factory.django import DjangoModelFactory

from .models import (
    IdentificationDocumentType,
    Institution,
    MobileOperator,
    Municipality,
    Profession,
    Province,
)


class ProvinceFactory(DjangoModelFactory):
    class Meta:
        model = Province
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"provincia-{n}")
    name = factory.Sequence(lambda n: f"Província {n}")


class MunicipalityFactory(DjangoModelFactory):
    class Meta:
        model = Municipality
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"municipio-{n}")
    name = factory.Sequence(lambda n: f"Município {n}")
    province = factory.SubFactory(ProvinceFactory)


class MobileOperatorFactory(DjangoModelFactory):
    class Meta:
        model = MobileOperator
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"operadora-{n}")
    name = factory.Sequence(lambda n: f"Operadora {n}")


class IdentificationDocumentTypeFactory(DjangoModelFactory):
    class Meta:
        model = IdentificationDocumentType
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"doc-{n}")
    name = factory.Sequence(lambda n: f"Documento {n}")


class ProfessionFactory(DjangoModelFactory):
    class Meta:
        model = Profession
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"profissao-{n}")
    name = factory.Sequence(lambda n: f"Profissão {n}")


class InstitutionFactory(DjangoModelFactory):
    class Meta:
        model = Institution

    name = factory.Sequence(lambda n: f"Escola Teste {n}")
