"""Tests for the local-dev demo data seeder (`apps.core.demo_data`).

Guarded by `settings.DEBUG` exactly like `create_dev_superuser` -- these
tests explicitly turn it on via `override_settings`, since the project's own
test settings (`config.settings.test`) run with `DEBUG=False`, same as any
real deployment.
"""

import pytest
from django.test import override_settings

from apps.academic.models import Schedule, SchoolClass
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.demo_data import DEMO_SCHOOL_CLASS_CODE, DEMO_STUDENT_COUNT, seed_demo_data
from apps.core.factories import InstitutionFactory
from apps.core.models import Institution
from apps.enrollment.models import Candidate, Enrollment, Guardian, Student, StudentGuardian
from apps.grading.models import FinalGrade, Grade

pytestmark = pytest.mark.django_db


@override_settings(DEBUG=False)
def test_does_nothing_when_debug_is_off():
    created = seed_demo_data()

    assert created is False
    assert not Institution.objects.exists()


@override_settings(DEBUG=True)
def test_seeds_a_full_demo_institution_when_none_exists_yet():
    created = seed_demo_data()

    assert created is True
    institution = Institution.objects.get()

    with tenant_context(institution.id):
        assert User.objects.filter(profile=Profile.INSTITUTION_ADMIN).count() == 1
        for profile in (
            Profile.PEDAGOGICAL_DIRECTION,
            Profile.SECRETARY,
            Profile.FINANCE,
            Profile.HR,
            Profile.LIBRARY,
            Profile.STUDENT,
            Profile.TEACHER,
            Profile.HOMEROOM_TEACHER,
            Profile.GUARDIAN,
        ):
            assert User.objects.filter(profile=profile).exists(), profile

        big_class = SchoolClass.objects.get(code=DEMO_SCHOOL_CLASS_CODE)
        assert Enrollment.objects.filter(school_class=big_class).count() >= DEMO_STUDENT_COUNT
        assert Student.objects.count() >= DEMO_STUDENT_COUNT
        assert Guardian.objects.count() >= DEMO_STUDENT_COUNT
        assert StudentGuardian.objects.count() >= DEMO_STUDENT_COUNT
        assert Candidate.objects.exists()
        assert Schedule.objects.exists()
        assert Grade.objects.filter(school_class=big_class).count() > 0
        assert FinalGrade.objects.exists()


@override_settings(DEBUG=True)
def test_seeds_into_an_existing_institution_instead_of_creating_a_second_one():
    """`apps.core.middleware.TenantMiddleware`'s own fallback for a Super
    Administrador with no institution "picker" (not built yet) is
    `Institution.objects.first()` -- seeding a second, separately named
    institution would just never be the one a Super Admin actually lands
    on. This must reuse whatever this node already has."""
    existing = InstitutionFactory(name="Escola Piloto FenixSchool")

    created = seed_demo_data()

    assert created is True
    assert Institution.objects.count() == 1
    with tenant_context(existing.id):
        assert SchoolClass.objects.filter(code=DEMO_SCHOOL_CLASS_CODE).exists()
        assert Student.objects.count() >= DEMO_STUDENT_COUNT


@override_settings(DEBUG=True)
def test_is_idempotent():
    first = seed_demo_data()
    second = seed_demo_data()

    assert first is True
    assert second is False
    assert Institution.objects.count() == 1


@override_settings(DEBUG=True)
def test_gives_root_the_seeded_institution():
    User.objects.create_user(
        username="root", profile=Profile.SUPER_ADMIN, is_staff=True, is_superuser=True
    )

    seed_demo_data()

    root = User.objects.get(username="root")
    assert root.institution is not None
    assert root.institution == Institution.objects.get()
