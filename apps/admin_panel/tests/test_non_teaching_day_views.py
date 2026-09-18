"""Tests for the Feriados/dias não lectivos screen (issue #20, RF-INST-07)."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import NonTeachingDay

pytestmark = pytest.mark.django_db

LIST_URL = reverse("admin_panel:non_teaching_day_list")
CREATE_URL = reverse("admin_panel:non_teaching_day_create")


def _origin():
    return uuid.uuid4()


@pytest.fixture
def admin_client(institution, verify_two_factor):
    admin = User.objects.create_user(
        username="admin1",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
        password="senha-forte-123",
    )
    admin.groups.add(Group.objects.get(name="Administrador da Instituição"))
    client = Client()
    client.login(username="admin1", password="senha-forte-123")
    verify_two_factor(client, admin)
    return client


@pytest.fixture
def pedagogical_client(institution, verify_two_factor):
    """Direção Pedagógica has view-only access (0003_profile_groups)."""
    user = User.objects.create_user(
        username="direcao1",
        institution=institution,
        profile=Profile.PEDAGOGICAL_DIRECTION,
        password="senha-forte-123",
    )
    user.groups.add(Group.objects.get(name="Direção Pedagógica"))
    client = Client()
    client.login(username="direcao1", password="senha-forte-123")
    verify_two_factor(client, user)
    return client


def test_requires_login(client):
    response = client.get(LIST_URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_lists_the_institutions_non_teaching_days(admin_client, institution):
    with tenant_context(institution.id):
        NonTeachingDay.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            date=date(2027, 1, 1),
            description="Ano Novo",
            scope=NonTeachingDay.Scope.NATIONAL,
        )

    response = admin_client.get(LIST_URL)

    assert response.status_code == 200
    assert "Ano Novo" in response.content.decode()


def test_seed_year_button_creates_national_holidays(admin_client, institution):
    response = admin_client.post(LIST_URL, {"seed_year": "2027"}, follow=True)

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert NonTeachingDay.objects.filter(
            institution=institution, date__year=2027, scope=NonTeachingDay.Scope.NATIONAL
        ).exists()


def test_pedagogical_direction_cannot_seed_holidays(pedagogical_client, institution):
    response = pedagogical_client.post(LIST_URL, {"seed_year": "2027"})

    assert response.status_code == 403
    with tenant_context(institution.id):
        assert not NonTeachingDay.objects.exists()


def test_create_a_custom_non_teaching_day(admin_client, institution):
    response = admin_client.post(
        CREATE_URL,
        {"date": "2027-06-10", "description": "Feriado municipal", "scope": "institucional"},
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        day = NonTeachingDay.objects.get(description="Feriado municipal")
    assert day.scope == NonTeachingDay.Scope.INSTITUTIONAL
    assert day.institution_id == institution.id


def test_edit_an_existing_non_teaching_day(admin_client, institution):
    with tenant_context(institution.id):
        day = NonTeachingDay.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            date=date(2027, 6, 10),
            description="Feriado municipal",
            scope=NonTeachingDay.Scope.INSTITUTIONAL,
        )

    response = admin_client.post(
        reverse("admin_panel:non_teaching_day_edit", args=[day.pk]),
        {
            "date": "2027-06-11",
            "description": "Feriado municipal (corrigido)",
            "scope": "institucional",
        },
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        day.refresh_from_db()
    assert day.description == "Feriado municipal (corrigido)"
    assert day.date == date(2027, 6, 11)


def test_delete_an_existing_non_teaching_day(admin_client, institution):
    with tenant_context(institution.id):
        day = NonTeachingDay.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            date=date(2027, 6, 10),
            description="Feriado municipal",
            scope=NonTeachingDay.Scope.INSTITUTIONAL,
        )

    response = admin_client.post(
        reverse("admin_panel:non_teaching_day_edit", args=[day.pk]), {"delete": "1"}, follow=True
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert not NonTeachingDay.objects.filter(pk=day.pk).exists()


def test_pedagogical_direction_cannot_delete(pedagogical_client, institution):
    with tenant_context(institution.id):
        day = NonTeachingDay.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            date=date(2027, 6, 10),
            description="Feriado municipal",
            scope=NonTeachingDay.Scope.INSTITUTIONAL,
        )

    response = pedagogical_client.post(
        reverse("admin_panel:non_teaching_day_edit", args=[day.pk]), {"delete": "1"}
    )

    assert response.status_code == 403
    with tenant_context(institution.id):
        assert NonTeachingDay.objects.filter(pk=day.pk).exists()


def test_cannot_edit_another_institutions_non_teaching_day(admin_client):
    from apps.core.models import Institution

    other_institution = Institution.objects.create(name="Outra Escola")
    with tenant_context(other_institution.id):
        day = NonTeachingDay.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            date=date(2027, 6, 10),
            description="Feriado de outra escola",
            scope=NonTeachingDay.Scope.INSTITUTIONAL,
        )

    response = admin_client.get(reverse("admin_panel:non_teaching_day_edit", args=[day.pk]))

    assert response.status_code == 404
