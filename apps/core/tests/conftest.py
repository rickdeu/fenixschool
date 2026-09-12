"""Shared fixtures for the `core` app's tests."""

import pytest
from django.apps import apps as django_apps
from django.db import connection, models

from apps.core.models import Institution, SyncedModel


@pytest.fixture
def institution_factory(transactional_db):
    """Return a factory function that creates a test `Institution`."""

    def _create(name="Test Institution"):
        return Institution.objects.create(name=name)

    return _create


@pytest.fixture
def synced_model_class(transactional_db):
    """Create a temporary table for a concrete model that inherits `SyncedModel`.

    Registered directly with the real `core` app (rather than an isolated one via
    Django's `isolate_apps` test helper) so the abstract `SyncedModel.institution`
    foreign key, defined as the lazy string reference `"core.Institution"`, can
    actually resolve against the already-installed `Institution` model. Requires
    `transactional_db` rather than the plain `db` fixture: SQLite's schema editor
    needs to disable foreign key constraint checking, which it cannot do in the
    middle of the outer transaction that the plain `db` fixture wraps every test
    in. The table is dropped, and the model unregistered again, after the test.
    """

    class ExampleSyncedModel(SyncedModel):
        name = models.CharField(max_length=100, default="")

        # Inheriting from `SyncedModel.Meta` (rather than declaring a bare `Meta`)
        # keeps the abstract parent's `indexes`; Django resets `abstract` to
        # `False` on this child regardless, so this does not make the concrete
        # model abstract too. See Django's "Meta inheritance" docs.
        class Meta(SyncedModel.Meta):
            app_label = "core"

    with connection.schema_editor() as editor:
        editor.create_model(ExampleSyncedModel)

    yield ExampleSyncedModel

    with connection.schema_editor() as editor:
        editor.delete_model(ExampleSyncedModel)

    django_apps.all_models["core"].pop(ExampleSyncedModel._meta.model_name, None)
    django_apps.clear_cache()
