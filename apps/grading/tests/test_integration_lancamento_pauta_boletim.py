"""Teste de integração ponta-a-ponta: lançamento de notas -> homologação ->
bloqueio de edição -> boletim (issue #156, docs/13-testes-e-qualidade.md
§13.1).

Percorre os ecrãs reais de um período lectivo completo através do `Client`
do Django, na ordem em que Docente/Secretaria os usariam -- em vez de
chamar `apps.grading.services` directamente, como os testes unitários de
cada etapa já fazem."""

import uuid
from decimal import Decimal
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.grading.models import Grade
from apps.grading.services import registar_media_final, set_institution_default_formula

pytestmark = pytest.mark.django_db

GRADE_SAVE_URL = reverse("grading:grade_cell_save")
PAUTA_URL = reverse("grading:pauta_detail")
BOLETIM_URL = reverse("grading:boletim")
BOLETIM_PDF_URL = reverse("grading:boletim_pdf")


@pytest.fixture
def teacher_client(teacher, schedule):
    # `schedule` (não usado directamente abaixo, mas obrigatório aqui): é o
    # que liga `teacher` a `school_class`/`subject` -- sem ele,
    # `lancar_ou_atualizar_nota` rejeita o lançamento
    # (`DocenteNaoAssociadoError`).
    client = Client()
    client.force_login(teacher)
    return client


@pytest.fixture
def admin_client(institution, verify_two_factor):
    admin = User.objects.create_user(
        username="admin1",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
        password="senha-forte-123",
        is_staff=True,
        is_superuser=True,
    )
    admin.groups.add(Group.objects.get(name="Administrador da Instituição"))
    client = Client()
    client.login(username="admin1", password="senha-forte-123")
    verify_two_factor(client, admin)
    return client


def test_full_term_flow_from_grade_entry_to_boletim(
    teacher_client,
    admin_client,
    institution,
    enrollment,
    subject,
    evaluation_type,
    academic_term,
    schedule,
):
    with tenant_context(institution.id):
        set_institution_default_formula(institution, {evaluation_type.name: Decimal("1")})

    # 1. Lançamento (RF-AVAL-01/issue #59): o Docente lança a nota via a
    # grelha (endpoint HTMX de gravação de uma célula).
    lancamento_response = teacher_client.post(
        GRADE_SAVE_URL,
        {
            "enrollment": str(enrollment.id),
            "subject": str(subject.id),
            "evaluation_type": str(evaluation_type.id),
            "academic_term": str(academic_term.id),
            "value": "15",
        },
    )

    assert lancamento_response.status_code == 200
    assert "error" not in lancamento_response.context
    grade = Grade.all_objects.get(
        enrollment=enrollment, subject=subject, evaluation_type=evaluation_type
    )
    assert grade.value == Decimal("15")
    assert grade.is_grade_report_closed is False

    # 2. Homologação (RF-AVAL-04/issue #60): a Secretaria/Direcção fecha a
    # pauta a partir do ecrã de detalhe.
    pauta_query = {
        "turma": str(enrollment.school_class_id),
        "disciplina": str(subject.id),
        "tipo": str(evaluation_type.id),
        "periodo": str(academic_term.id),
    }
    homologar_response = admin_client.post(
        f"{PAUTA_URL}?{urlencode(pauta_query)}",
        {"grade_ids": [str(grade.pk)], "action": "homologar"},
        follow=True,
    )

    assert homologar_response.status_code == 200
    grade.refresh_from_db()
    assert grade.is_grade_report_closed is True

    # 3. Bloqueio de edição (RF-AVAL-04's próprio critério de aceitação):
    # o Docente já não consegue alterar uma nota de uma pauta homologada.
    edit_attempt_response = teacher_client.post(
        GRADE_SAVE_URL,
        {
            "enrollment": str(enrollment.id),
            "subject": str(subject.id),
            "evaluation_type": str(evaluation_type.id),
            "academic_term": str(academic_term.id),
            "value": "20",
        },
    )

    assert edit_attempt_response.status_code == 200
    assert "já está fechada" in edit_attempt_response.content.decode()
    grade.refresh_from_db()
    assert grade.value == Decimal("15")  # inalterada.

    # 4. Cálculo da média final -- ainda não exposto por nenhum ecrã (ver
    # `apps.grading.tests.test_boletim`'s mesma chamada directa), mas é o
    # que o boletim, a seguir, mostra.
    with tenant_context(institution.id):
        registar_media_final(
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            origin_node_id=uuid.uuid4(),
        )

    # 5. Geração de boletim (RF-REL-04/issue #97).
    boletim_response = admin_client.get(
        BOLETIM_URL, {"aluno": str(enrollment.id), "periodo": str(academic_term.id)}
    )

    assert boletim_response.status_code == 200
    boletim_content = boletim_response.content.decode()
    assert subject.name in boletim_content
    assert "15,00" in boletim_content  # RF-INST-06: pt-formatted (vírgula).

    pdf_response = admin_client.post(
        BOLETIM_PDF_URL, {"aluno": str(enrollment.id), "periodo": str(academic_term.id)}
    )

    assert pdf_response.status_code == 200
    assert pdf_response["Content-Type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF-")
