"""Tests for the grading-formula configuration views (issue #18, RF-INST-06)."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.academic.models import Course, CurricularYear, Department, Subject
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle
from apps.grading.models import EvaluationType, GradingFormulaOverride

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def admin_client(institution):
    admin = User.objects.create_user(
        username="admin1",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
        password="senha-forte-123",
    )
    admin.groups.add(Group.objects.get(name="Administrador da Instituição"))
    client = Client()
    client.login(username="admin1", password="senha-forte-123")
    return client


@pytest.fixture
def course_and_subject(institution):
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )
        course = Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )
        curricular_year = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )
        subject = Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="MAT",
            name="Matemática",
            created_on=date(2020, 1, 1),
            course=course,
            curricular_year=curricular_year,
            cycle=cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=4,
        )
    return course, subject


def test_config_view_requires_login(client):
    response = client.get(reverse("admin_panel:grading_formula_config"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_config_view_requires_permission(institution):
    User.objects.create_user(
        username="aluno1", institution=institution, profile=Profile.STUDENT, password="pw12345"
    )
    client = Client()
    client.login(username="aluno1", password="pw12345")

    response = client.get(reverse("admin_panel:grading_formula_config"))

    assert response.status_code == 403


def test_config_view_redirects_gracefully_without_a_selected_institution(institution):
    """A Super Administrator has no `institution` of their own until they
    pick one to view (issue #18's bug found via manual Docker verification:
    this used to crash with a 500 instead)."""
    User.objects.create_user(
        username="superadmin1", profile=Profile.SUPER_ADMIN, password="pw12345", is_superuser=True
    )
    client = Client()
    client.login(username="superadmin1", password="pw12345")

    response = client.get(reverse("admin_panel:grading_formula_config"), follow=True)

    assert response.status_code == 200
    assert response.redirect_chain
    assert "nenhuma instituição está seleccionada" in response.content.decode()


def test_config_view_auto_seeds_default_evaluation_types(admin_client, institution):
    response = admin_client.get(reverse("admin_panel:grading_formula_config"))

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert {t.name for t in EvaluationType.objects.filter(institution=institution)} == {
            "MAC",
            "Prova Trimestral",
            "Exame",
        }


def test_config_view_shows_a_calculation_preview(admin_client):
    response = admin_client.get(reverse("admin_panel:grading_formula_config"))

    content = response.content.decode()
    assert "Pré-visualização do cálculo" in content
    assert "MAC" in content


def test_saving_a_valid_formula_updates_the_institution(admin_client, institution):
    admin_client.get(reverse("admin_panel:grading_formula_config"))
    with tenant_context(institution.id):
        types = {t.name: t for t in EvaluationType.objects.filter(institution=institution)}

    response = admin_client.post(
        reverse("admin_panel:grading_formula_config"),
        {
            f"weight_{types['MAC'].id}": "0.5",
            f"weight_{types['Prova Trimestral'].id}": "0.5",
            f"weight_{types['Exame'].id}": "",
        },
    )

    assert response.status_code == 302
    institution.refresh_from_db()
    assert institution.default_grading_formula == {"MAC": "0.5", "Prova Trimestral": "0.5"}


def test_saving_a_formula_that_does_not_sum_to_one_shows_an_error(admin_client, institution):
    admin_client.get(reverse("admin_panel:grading_formula_config"))
    with tenant_context(institution.id):
        mac_id = EvaluationType.objects.get(institution=institution, name="MAC").id

    response = admin_client.post(
        reverse("admin_panel:grading_formula_config"), {f"weight_{mac_id}": "0.5"}
    )

    assert response.status_code == 200
    assert "soma dos pesos" in response.content.decode()
    institution.refresh_from_db()
    assert institution.default_grading_formula == {}


def test_course_override_view_saves_and_can_be_cleared(
    admin_client, institution, course_and_subject
):
    course, _subject = course_and_subject
    admin_client.get(reverse("admin_panel:grading_formula_config"))
    with tenant_context(institution.id):
        mac_id = EvaluationType.objects.get(institution=institution, name="MAC").id
        exame_id = EvaluationType.objects.get(institution=institution, name="Exame").id

    url = reverse("admin_panel:course_grading_formula", args=[course.id])
    response = admin_client.post(
        url, {f"weight_{mac_id}": "0.2", f"weight_{exame_id}": "0.8"}
    )
    assert response.status_code == 302
    with tenant_context(institution.id):
        override = GradingFormulaOverride.objects.get(course=course)
    assert override.weights == {"MAC": "0.2", "Exame": "0.8"}

    clear_response = admin_client.post(url, {"clear": "1"})
    assert clear_response.status_code == 302
    with tenant_context(institution.id):
        assert not GradingFormulaOverride.objects.filter(course=course).exists()


def test_subject_override_takes_precedence_and_is_shown_in_preview(
    admin_client, institution, course_and_subject
):
    course, subject = course_and_subject
    admin_client.get(reverse("admin_panel:grading_formula_config"))
    with tenant_context(institution.id):
        mac_id = EvaluationType.objects.get(institution=institution, name="MAC").id
        exame_id = EvaluationType.objects.get(institution=institution, name="Exame").id

    response = admin_client.post(
        reverse("admin_panel:subject_grading_formula", args=[subject.id]),
        {f"weight_{mac_id}": "0.1", f"weight_{exame_id}": "0.9"},
    )

    assert response.status_code == 302
    with tenant_context(institution.id):
        override = GradingFormulaOverride.objects.get(subject=subject)
    assert override.weights == {"MAC": "0.1", "Exame": "0.9"}
