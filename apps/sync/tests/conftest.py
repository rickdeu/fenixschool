"""Shared fixtures for the `sync` app's tests."""

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

    Mirrors `apps/core/tests/conftest.py`'s fixture of the same name -- see its
    docstring for why `transactional_db` is required here. Registered under
    the `sync` app label (rather than `core`) since these tests live here.
    """

    class ExampleSyncedModel(SyncedModel):
        name = models.CharField(max_length=100, default="")

        class Meta(SyncedModel.Meta):
            app_label = "sync"

    with connection.schema_editor() as editor:
        editor.create_model(ExampleSyncedModel)

    yield ExampleSyncedModel

    with connection.schema_editor() as editor:
        editor.delete_model(ExampleSyncedModel)

    django_apps.all_models["sync"].pop(ExampleSyncedModel._meta.model_name, None)
    django_apps.clear_cache()
