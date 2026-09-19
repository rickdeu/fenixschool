"""Tests for the grelha de lançamento de notas (issue #59, RF-AVAL-01,
docs/06-modulos-e-funcionalidades.md §6.6)."""

import uuid
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile
from apps.core.context import tenant_context
from apps.grading.models import Grade

pytestmark = pytest.mark.django_db

SELECTION_URL = reverse("grading:grade_grid_selection")
GRID_URL = reverse("grading:grade_grid")
CELL_SAVE_URL = reverse("grading:grade_cell_save")


def _origin():
    return uuid.uuid4()


@pytest.fixture
def teacher_client(teacher):
    client = Client()
    client.force_login(teacher)
    return client


def test_anonymous_user_is_redirected_to_login(client):
    response = client.get(SELECTION_URL)

    assert response.status_code == 302


def test_non_teacher_profile_is_forbidden(institution, user_factory):
    secretary = user_factory(profile=Profile.SECRETARY, institution=institution, password="x")
    client = Client()
    client.force_login(secretary)

    response = client.get(SELECTION_URL)

    assert response.status_code == 403


def test_super_admin_is_never_blocked_by_the_docente_profile_check(
    institution, user_factory, verify_two_factor
):
    """ "Super Administrador deve ter acesso a tudo, sem restrição alguma" --
    a Super Admin's own profile is neither Docente nor Diretor de Turma, but
    `docente_required` (via `apps.accounts.permissions.require_profile`)
    must still let them open the screen."""
    super_admin = user_factory(profile=Profile.SUPER_ADMIN, institution=institution)
    client = Client()
    client.force_login(super_admin)
    verify_two_factor(client, super_admin)

    response = client.get(SELECTION_URL)

    assert response.status_code == 200


def test_super_admin_sees_every_turma_disciplina_even_without_a_schedule(
    institution, user_factory, verify_two_factor, school_class, subject
):
    """Unlike a real Docente (`test_selection_view_shows_nothing_for_a_teacher_with_no_schedule`),
    a Super Admin isn't limited to their own `Schedule` rows -- they have
    none, and still see every turma/disciplina valid for that turma's ano
    curricular."""
    super_admin = user_factory(profile=Profile.SUPER_ADMIN, institution=institution)
    client = Client()
    client.force_login(super_admin)
    verify_two_factor(client, super_admin)

    response = client.get(SELECTION_URL)

    content = response.content.decode()
    assert school_class.designation in content
    assert subject.name in content


def test_super_admin_can_open_and_save_into_a_grid_with_no_schedule_of_their_own(
    institution,
    user_factory,
    verify_two_factor,
    enrollment,
    school_class,
    subject,
    evaluation_type,
    academic_term,
):
    super_admin = user_factory(profile=Profile.SUPER_ADMIN, institution=institution)
    client = Client()
    client.force_login(super_admin)
    verify_two_factor(client, super_admin)

    grid_response = client.get(
        GRID_URL,
        {
            "turma": school_class.id,
            "disciplina": subject.id,
            "tipo": evaluation_type.id,
            "periodo": academic_term.id,
        },
    )
    assert grid_response.status_code == 200

    save_response = client.post(
        CELL_SAVE_URL,
        {
            "enrollment": str(enrollment.id),
            "subject": str(subject.id),
            "evaluation_type": str(evaluation_type.id),
            "academic_term": str(academic_term.id),
            "value": "18",
        },
    )

    assert save_response.status_code == 200
    assert "Gravado" in save_response.content.decode()


def test_sidebar_shows_the_lancar_notas_link_to_super_admin(
    institution, user_factory, verify_two_factor
):
    """Regression test: `docente_required` letting a Super Admin through
    doesn't help if the sidebar link itself is still hidden from them --
    `templates/base.html` gated this section on a raw `user.profile`
    check, which (unlike `perms.*`) isn't automatically satisfied by
    `is_superuser`."""
    super_admin = user_factory(profile=Profile.SUPER_ADMIN, institution=institution)
    client = Client()
    client.force_login(super_admin)
    verify_two_factor(client, super_admin)

    response = client.get(SELECTION_URL)

    assert "Lançar notas" in response.content.decode()


def test_selection_view_lists_the_teachers_own_schedule_assignments(
    teacher_client, schedule, school_class, subject
):
    response = teacher_client.get(SELECTION_URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert school_class.designation in content
    assert subject.name in content


def test_selection_view_shows_nothing_for_a_teacher_with_no_schedule(institution, user_factory):
    other_teacher = user_factory(profile=Profile.TEACHER, institution=institution, password="x")
    client = Client()
    client.force_login(other_teacher)

    response = client.get(SELECTION_URL)

    assert response.status_code == 200
    assert "não está associado" in response.content.decode().lower()


def test_selection_view_redirects_to_the_grid_with_the_chosen_assignment(
    teacher_client, schedule, school_class, subject, evaluation_type, academic_term
):
    response = teacher_client.post(
        SELECTION_URL,
        {
            "assignment": f"{school_class.id}:{subject.id}",
            "evaluation_type": str(evaluation_type.id),
            "academic_term": str(academic_term.id),
        },
    )

    assert response.status_code == 302
    assert str(school_class.id) in response.url
    assert str(subject.id) in response.url


def test_grid_view_lists_the_class_students(
    teacher_client, schedule, enrollment, school_class, subject, evaluation_type, academic_term
):
    response = teacher_client.get(
        GRID_URL,
        {
            "turma": school_class.id,
            "disciplina": subject.id,
            "tipo": evaluation_type.id,
            "periodo": academic_term.id,
        },
    )

    assert response.status_code == 200
    assert "Yolene Hangalo" in response.content.decode()


def test_grid_view_is_forbidden_for_a_teacher_without_a_matching_schedule(
    institution, enrollment, school_class, subject, evaluation_type, academic_term, user_factory
):
    other_teacher = user_factory(profile=Profile.TEACHER, institution=institution, password="x")
    client = Client()
    client.force_login(other_teacher)

    response = client.get(
        GRID_URL,
        {
            "turma": school_class.id,
            "disciplina": subject.id,
            "tipo": evaluation_type.id,
            "periodo": academic_term.id,
        },
    )

    assert response.status_code == 403


def test_cell_save_creates_a_grade(
    teacher_client, institution, schedule, enrollment, subject, evaluation_type, academic_term
):
    response = teacher_client.post(
        CELL_SAVE_URL,
        {
            "enrollment": str(enrollment.id),
            "subject": str(subject.id),
            "evaluation_type": str(evaluation_type.id),
            "academic_term": str(academic_term.id),
            "value": "15.5",
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Gravado" in content
    with tenant_context(institution.id):
        grade = Grade.objects.get(
            enrollment=enrollment, subject=subject, evaluation_type=evaluation_type
        )
    assert grade.value == Decimal("15.5")
    # RF-AVAL-01/03 (issue #57): "nível qualitativo mostrado junto ao valor
    # numérico" -- not just computable on the model, actually rendered.
    assert grade.qualitative_level.qualitative_level in content
    # A nota persiste correctamente na base de dados, mas reportado ao vivo:
    # o valor devolvido no `value="..."` de um `<input type="number">` tem
    # de usar sempre ponto decimal -- "15,5" (a formatação por omissão em
    # pt, activa neste projecto) não é um número válido para esse tipo de
    # campo, e o browser mostra o campo como vazio (parece que "a nota
    # desaparece" ao recarregar, mesmo já gravada).
    assert 'value="15.5"' in content
    assert 'value="15,5"' not in content


def test_cell_save_updates_an_existing_grade_instead_of_erroring(
    teacher_client,
    institution,
    schedule,
    enrollment,
    subject,
    evaluation_type,
    academic_term,
    teacher,
):
    with tenant_context(institution.id):
        Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment.student,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            evaluation_type=evaluation_type,
            value=Decimal("10"),
            teacher=teacher,
        )

    response = teacher_client.post(
        CELL_SAVE_URL,
        {
            "enrollment": str(enrollment.id),
            "subject": str(subject.id),
            "evaluation_type": str(evaluation_type.id),
            "academic_term": str(academic_term.id),
            "value": "17",
        },
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert Grade.objects.filter(enrollment=enrollment, subject=subject).count() == 1
        grade = Grade.objects.get(enrollment=enrollment, subject=subject)
    assert grade.value == Decimal("17.0")


def test_cell_save_rejects_a_value_outside_the_0_20_scale(
    teacher_client, institution, schedule, enrollment, subject, evaluation_type, academic_term
):
    response = teacher_client.post(
        CELL_SAVE_URL,
        {
            "enrollment": str(enrollment.id),
            "subject": str(subject.id),
            "evaluation_type": str(evaluation_type.id),
            "academic_term": str(academic_term.id),
            "value": "25",
        },
    )

    assert response.status_code == 200
    assert "fora da escala" in response.content.decode().lower()
    with tenant_context(institution.id):
        assert not Grade.objects.filter(enrollment=enrollment, subject=subject).exists()


def test_cell_save_rejects_a_teacher_not_associated_with_the_turma_disciplina(
    institution, enrollment, subject, evaluation_type, academic_term, user_factory
):
    other_teacher = user_factory(profile=Profile.TEACHER, institution=institution, password="x")
    client = Client()
    client.force_login(other_teacher)

    response = client.post(
        CELL_SAVE_URL,
        {
            "enrollment": str(enrollment.id),
            "subject": str(subject.id),
            "evaluation_type": str(evaluation_type.id),
            "academic_term": str(academic_term.id),
            "value": "15",
        },
    )

    assert response.status_code == 200
    assert "não está associado" in response.content.decode().lower()
    with tenant_context(institution.id):
        assert not Grade.objects.filter(enrollment=enrollment, subject=subject).exists()


def test_cell_save_blocks_editing_a_grade_in_a_closed_pauta(
    teacher_client,
    institution,
    schedule,
    enrollment,
    subject,
    evaluation_type,
    academic_term,
    teacher,
):
    with tenant_context(institution.id):
        grade = Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment.student,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            evaluation_type=evaluation_type,
            value=Decimal("10"),
            teacher=teacher,
        )
        grade.is_grade_report_closed = True
        grade.save(authorize_closed_edit=True)

    response = teacher_client.post(
        CELL_SAVE_URL,
        {
            "enrollment": str(enrollment.id),
            "subject": str(subject.id),
            "evaluation_type": str(evaluation_type.id),
            "academic_term": str(academic_term.id),
            "value": "18",
        },
    )

    assert response.status_code == 200
    assert "pauta já está fechada" in response.content.decode().lower()
    with tenant_context(institution.id):
        grade.refresh_from_db()
    assert grade.value == Decimal("10.0")
