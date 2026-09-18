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
from apps.core.demo_data import DEMO_INSTITUTION_NAME, DEMO_STUDENT_COUNT, seed_demo_data
from apps.core.models import Institution
from apps.enrollment.models import Candidate, Enrollment, Guardian, Student, StudentGuardian
from apps.grading.models import FinalGrade, Grade

pytestmark = pytest.mark.django_db


@override_settings(DEBUG=False)
def test_does_nothing_when_debug_is_off():
    created = seed_demo_data()

    assert created is False
    assert not Institution.objects.filter(name=DEMO_INSTITUTION_NAME).exists()


@override_settings(DEBUG=True)
def test_seeds_a_full_demo_institution():
    created = seed_demo_data()

    assert created is True
    institution = Institution.objects.get(name=DEMO_INSTITUTION_NAME)

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

        big_class = SchoolClass.objects.get(code="10A")
        assert Enrollment.objects.filter(school_class=big_class).count() >= DEMO_STUDENT_COUNT
        assert Student.objects.count() >= DEMO_STUDENT_COUNT
        assert Guardian.objects.count() >= DEMO_STUDENT_COUNT
        assert StudentGuardian.objects.count() >= DEMO_STUDENT_COUNT
        assert Candidate.objects.exists()
        assert Schedule.objects.exists()
        assert Grade.objects.filter(school_class=big_class).count() > 0
        assert FinalGrade.objects.exists()


@override_settings(DEBUG=True)
def test_is_idempotent():
    first = seed_demo_data()
    second = seed_demo_data()

    assert first is True
    assert second is False
    assert Institution.objects.filter(name=DEMO_INSTITUTION_NAME).count() == 1


@override_settings(DEBUG=True)
def test_gives_root_the_demo_institution():
    User.objects.create_user(
        username="root", profile=Profile.SUPER_ADMIN, is_staff=True, is_superuser=True
    )

    seed_demo_data()

    root = User.objects.get(username="root")
    assert root.institution is not None
    assert root.institution.name == DEMO_INSTITUTION_NAME
