"""Tests for justificação de faltas com anexo opcional (issue #67,
RF-FREQ-02)."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.attendance.models import Attendance
from apps.attendance.services import EstadoInvalidoParaJustificacaoError, justificar_falta
from apps.core.context import tenant_context

pytestmark = pytest.mark.django_db

MONDAY = date(2026, 3, 2)

LIST_URL = reverse("attendance:absence_list")


def _origin():
    return uuid.uuid4()


@pytest.fixture
def secretary_client(institution, verify_two_factor):
    secretary = User.objects.create_user(
        username="secretaria1",
        institution=institution,
        profile=Profile.SECRETARY,
        password="senha-forte-123",
    )
    secretary.groups.add(Group.objects.get(name="Secretaria Escolar"))
    client = Client()
    client.login(username="secretaria1", password="senha-forte-123")
    verify_two_factor(client, secretary)
    return client


@pytest.fixture
def absence(institution, enrollment, student, schedule, teacher):
    with tenant_context(institution.id):
        return Attendance.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            enrollment=enrollment,
            schedule=schedule,
            date=MONDAY,
            status=Attendance.Status.ABSENT,
            registered_by=teacher,
        )


def test_justificar_falta_changes_status_and_records_text(institution, absence, teacher):
    with tenant_context(institution.id):
        justificar_falta(attendance=absence, text="Consulta médica.", justified_by=teacher)

    absence.refresh_from_db()
    assert absence.status == Attendance.Status.JUSTIFIED_ABSENT
    assert absence.justification_text == "Consulta médica."
    assert not absence.justification_attachment


def test_justificar_falta_accepts_an_optional_attachment(institution, absence, teacher):
    attachment = SimpleUploadedFile("atestado.pdf", b"conteudo", content_type="application/pdf")

    with tenant_context(institution.id):
        justificar_falta(
            attendance=absence,
            text="Atestado em anexo.",
            justified_by=teacher,
            attachment=attachment,
        )

    absence.refresh_from_db()
    assert absence.justification_attachment
    assert absence.justification_attachment.name.endswith("atestado.pdf")


def test_justificar_falta_rejects_a_present_record(
    institution, enrollment, student, schedule, teacher
):
    with tenant_context(institution.id):
        present = Attendance.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            enrollment=enrollment,
            schedule=schedule,
            date=MONDAY,
            status=Attendance.Status.PRESENT,
            registered_by=teacher,
        )

        with pytest.raises(EstadoInvalidoParaJustificacaoError):
            justificar_falta(attendance=present, text="Não faz sentido.", justified_by=teacher)


def test_absence_list_forbidden_for_a_teacher(institution, teacher):
    client = Client()
    client.force_login(teacher)

    response = client.get(LIST_URL)

    assert response.status_code == 403


def test_absence_list_shows_unjustified_absences_for_the_chosen_class(
    secretary_client, absence, school_class
):
    response = secretary_client.get(LIST_URL, {"turma": str(school_class.id)})

    assert response.status_code == 200
    assert "Yolene Hangalo" in response.content.decode()


def test_absence_list_shows_every_class_with_absences_without_a_filter(
    secretary_client, absence, school_class
):
    response = secretary_client.get(LIST_URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert school_class.designation in content
    assert "Yolene Hangalo" in content


def test_justify_absence_view_saves_text_and_attachment(tmp_path, secretary_client, absence):
    with override_settings(MEDIA_ROOT=tmp_path):
        url = reverse("attendance:justify_absence", args=[absence.id])
        attachment = SimpleUploadedFile(
            "atestado.pdf", b"conteudo", content_type="application/pdf"
        )

        response = secretary_client.post(
            url,
            {"justification_text": "Consulta médica.", "justification_attachment": attachment},
            follow=True,
        )

        assert response.status_code == 200
        absence.refresh_from_db()
        assert absence.status == Attendance.Status.JUSTIFIED_ABSENT
        assert absence.justification_attachment


def test_attachment_download_is_forbidden_without_permission(institution, teacher, absence):
    client = Client()
    client.force_login(teacher)

    url = reverse("attendance:justification_attachment", args=[absence.id])
    response = client.get(url)

    assert response.status_code == 403


def test_attachment_download_streams_the_file_for_an_authorized_user(
    tmp_path, institution, secretary_client, absence
):
    with override_settings(MEDIA_ROOT=tmp_path):
        with tenant_context(institution.id):
            absence.justification_attachment.save(
                "atestado.pdf", SimpleUploadedFile("atestado.pdf", b"conteudo-secreto")
            )

        url = reverse("attendance:justification_attachment", args=[absence.id])
        response = secretary_client.get(url)

        assert response.status_code == 200
        assert b"".join(response.streaming_content) == b"conteudo-secreto"


def test_attachment_url_is_never_rendered_in_the_justify_page(
    tmp_path, institution, secretary_client, absence
):
    with override_settings(MEDIA_ROOT=tmp_path):
        with tenant_context(institution.id):
            absence.justification_attachment.save(
                "atestado.pdf", SimpleUploadedFile("atestado.pdf", b"conteudo-secreto")
            )
        url = reverse("attendance:justify_absence", args=[absence.id])

        response = secretary_client.get(url)

        content = response.content.decode()
        assert absence.justification_attachment.url not in content
