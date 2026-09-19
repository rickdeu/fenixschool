"""Tests for the public pre-application form (issue #102, RF-PUB-03)."""

import uuid
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.academic.models import Course, Department
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, IdentificationDocumentType
from apps.enrollment.models import Candidate

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


@pytest.fixture
def course(institution):
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )
        return Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )


def test_redirects_to_the_setup_wizard_when_no_institution_exists():
    response = Client().get(reverse("public_site:pre_application"))

    assert response.status_code == 302
    assert response.url == reverse("core:setup_wizard")


def test_is_accessible_without_login(institution, course):
    response = Client().get(reverse("public_site:pre_application"))

    assert response.status_code == 200


def test_valid_submission_creates_a_pending_candidate(institution, course, document_type):
    response = Client().post(
        reverse("public_site:pre_application"),
        data={
            "full_name": "Ana Kavungo",
            "birth_date": "2010-05-20",
            "document_type": document_type.code,
            "document_number": "004928474HA038",
            "document_expiry_date": "2030-01-01",
            "desired_course": str(course.pk),
            "contact": "923000000",
        },
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        candidate = Candidate.objects.get(full_name="Ana Kavungo")
    assert candidate.status == Candidate.Status.PENDING
    assert candidate.institution_id == institution.id
    assert candidate.desired_course_id == course.id
    assert candidate.contact == "923000000"
    assert candidate.document_type_id == document_type.code
    assert candidate.document_number == "004928474HA038"


def test_missing_required_fields_shows_validation_errors_and_creates_nothing(institution, course):
    response = Client().post(reverse("public_site:pre_application"), data={})

    assert response.status_code == 200
    assert "obrigatório" in response.content.decode() or "campo" in response.content.decode()
    with tenant_context(institution.id):
        assert not Candidate.objects.exists()


def test_desired_course_choices_never_leak_another_institutions_courses(institution, course):
    from apps.core.models import Institution

    other_institution = Institution.objects.create(name="Outra Escola")
    with tenant_context(other_institution.id):
        other_department = Department.objects.create(
            institution=other_institution, origin_node_id=_origin(), name="Letras"
        )
        other_cycle = AcademicCycle.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            designation="1.º Ciclo",
            order=1,
        )
        other_course = Course.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            code="LET",
            name="Letras Modernas",
            created_on=date(2020, 1, 1),
            department=other_department,
            cycle=other_cycle,
            duration_years=4,
        )

    response = Client().post(
        reverse("public_site:pre_application"),
        data={
            "full_name": "João Bumba",
            "birth_date": "2009-01-01",
            "desired_course": str(other_course.pk),
            "contact": "923111111",
        },
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert not Candidate.objects.filter(full_name="João Bumba").exists()


def _apply(document_number, course, document_type, *, full_name="Ana Kavungo"):
    return Client().post(
        reverse("public_site:pre_application"),
        data={
            "full_name": full_name,
            "birth_date": "2010-05-20",
            "document_type": document_type.code,
            "document_number": document_number,
            "document_expiry_date": "2030-01-01",
            "desired_course": str(course.pk),
            "contact": "923000000",
        },
    )


def test_valid_submission_issues_a_pdf_receipt_with_a_reserved_number(
    institution, course, document_type
):
    response = _apply("004928474HA038", course, document_type)

    assert response.status_code == 200
    with tenant_context(institution.id):
        candidate = Candidate.objects.get(full_name="Ana Kavungo")
    assert candidate.application_receipt is not None
    assert candidate.application_receipt.formatted_number.startswith("COMPROVATIVO-CANDIDATURA/")
    assert candidate.application_receipt.issued_by is None
    assert response.context["candidate"].application_receipt is not None


def test_a_second_application_with_the_same_document_number_is_blocked(
    institution, course, document_type
):
    _apply("004928474HA038", course, document_type)

    response = _apply("004928474HA038", course, document_type, full_name="Ana Segunda Vez")

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert not Candidate.objects.filter(full_name="Ana Segunda Vez").exists()
        assert Candidate.objects.filter(document_number="004928474HA038").count() == 1


def test_a_rejected_candidate_may_re_apply(institution, course, document_type):
    _apply("004928474HA038", course, document_type)
    with tenant_context(institution.id):
        Candidate.objects.filter(document_number="004928474HA038").update(
            status=Candidate.Status.REJECTED
        )

    response = _apply("004928474HA038", course, document_type, full_name="Ana Segunda Vez")

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert Candidate.objects.filter(full_name="Ana Segunda Vez").exists()


def test_receipt_lookup_by_document_number_returns_the_pdf(institution, course, document_type):
    _apply("004928474HA038", course, document_type)
    with tenant_context(institution.id):
        candidate = Candidate.objects.get(document_number="004928474HA038")

    response = Client().post(
        reverse("public_site:application_receipt"),
        data={"document_number": "004928474HA038"},
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    with tenant_context(institution.id):
        candidate.refresh_from_db()
    from apps.reports.models import IssuedDocument

    assert IssuedDocument.all_objects.filter(document_type="comprovativo-candidatura").count() == 1


def test_receipt_lookup_with_unknown_document_number_shows_an_error(institution, course):
    response = Client().post(
        reverse("public_site:application_receipt"),
        data={"document_number": "does-not-exist"},
    )

    assert response.status_code == 200
    assert "Não encontrámos" in response.content.decode()
