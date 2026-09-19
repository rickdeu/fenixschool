"""Tests for the setup wizard (issue #17, docs/04-arquitetura-tecnica.md §4.4.2)."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import Institution, NonTeachingDay
from apps.core.services import setup_institution
from apps.grading.models import EvaluationType

pytestmark = pytest.mark.django_db

VALID_POST_DATA = {
    "name": "Escola Piloto",
    "tax_id": "",
    "ministry_of_education_code": "",
    "email": "",
    "website": "",
    "username": "gestor1",
    "email_manager": "",
    "first_name": "Gestor",
    "last_name": "Um",
    "phone": "",
    "password": "uma-password-bastante-forte-123",
    "password_confirmation": "uma-password-bastante-forte-123",
}


def test_wizard_is_reachable_when_no_institution_exists(client):
    response = client.get(reverse("core:setup_wizard"))

    assert response.status_code == 200
    assert "institution_form" in response.context
    assert "manager_form" in response.context


def test_wizard_creates_institution_and_manager_atomically(client):
    response = client.post(reverse("core:setup_wizard"), VALID_POST_DATA)

    assert response.status_code == 302
    institution = Institution.objects.get()
    assert institution.name == "Escola Piloto"
    manager = User.objects.get()
    assert manager.institution == institution
    assert manager.profile == Profile.INSTITUTION_ADMIN
    assert manager.check_password("uma-password-bastante-forte-123")


def test_wizard_seeds_a_working_default_grading_formula(client):
    """Issue #18: an institution must have a working formula from day one,
    not an empty one blocking every average calculation until an
    Administrator happens to visit the configuration screen."""
    client.post(reverse("core:setup_wizard"), VALID_POST_DATA)

    institution = Institution.objects.get()
    assert institution.default_grading_formula
    assert sum(Decimal(w) for w in institution.default_grading_formula.values()) == Decimal("1.0")
    with tenant_context(institution.id):
        assert {t.name for t in EvaluationType.objects.filter(institution=institution)} == {
            "MAC",
            "Prova Trimestral",
            "Exame",
        }


def test_wizard_registers_this_nodes_own_sync_identity(client, tmp_path, settings):
    """Issue #123: a instalação gera a chave própria deste Node -- nunca
    exige que o Administrador a configure à mão."""
    from apps.sync.models import Node

    settings.NODE_PRIVATE_KEY_PATH = str(tmp_path / "node_private_key.pem")

    client.post(reverse("core:setup_wizard"), VALID_POST_DATA)

    institution = Institution.objects.get()
    node = Node.objects.get()
    assert node.node_type == Node.NodeType.LOCAL
    assert node.institution == institution
    assert node.public_key.startswith("-----BEGIN PUBLIC KEY-----")


def test_wizard_preloads_this_and_next_years_national_holidays(client):
    """Issue #20: national holidays must be pre-loaded at installation, not
    left for an Administrator to type in by hand before the calendar means
    anything."""
    client.post(reverse("core:setup_wizard"), VALID_POST_DATA)

    institution = Institution.objects.get()
    today = date.today()
    with tenant_context(institution.id):
        holidays = NonTeachingDay.objects.filter(
            institution=institution, scope=NonTeachingDay.Scope.NATIONAL
        )
        assert holidays.filter(date__year=today.year).exists()
        assert holidays.filter(date__year=today.year + 1).exists()
        assert holidays.get(date=date(today.year, 1, 1)).description == "Ano Novo"


def test_wizard_rejects_mismatched_passwords_without_creating_anything(client):
    data = {**VALID_POST_DATA, "password_confirmation": "uma-password-diferente"}

    response = client.post(reverse("core:setup_wizard"), data)

    assert response.status_code == 200
    assert not Institution.objects.exists()
    assert not User.objects.exists()


def test_wizard_is_inaccessible_once_an_institution_already_exists(client, institution):
    get_response = client.get(reverse("core:setup_wizard"))
    post_response = client.post(reverse("core:setup_wizard"), VALID_POST_DATA)

    assert get_response.status_code == 302
    assert get_response.url == reverse("admin:login")
    assert post_response.status_code == 302
    assert post_response.url == reverse("admin:login")
    # The second (rejected) POST must not have created a second institution.
    assert Institution.objects.count() == 1


def test_setup_institution_rolls_back_the_institution_if_the_manager_fails():
    # A pre-existing user with the same username the wizard will try to
    # reuse -- `create_user()` gets past Python argument binding fine, but
    # fails at the database's unique constraint, which is the case worth
    # proving atomicity against (a plain Python-level error before any
    # write wouldn't demonstrate a rollback at all).
    User.objects.create_user(username="gestor1")

    with pytest.raises(IntegrityError):
        setup_institution(
            institution_data={"name": "Escola Que Vai Falhar"},
            manager_data={"username": "gestor1"},
        )

    assert not Institution.objects.filter(name="Escola Que Vai Falhar").exists()
