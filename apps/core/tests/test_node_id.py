"""Tests for `apps.core.context.get_current_node_id`."""

import uuid

from django.test import override_settings

from apps.core.context import get_current_node_id


def test_falls_back_to_a_stable_per_process_id_when_unconfigured():
    with override_settings(NODE_ID=""):
        first = get_current_node_id()
        second = get_current_node_id()

    assert first == second
    assert isinstance(first, uuid.UUID)


def test_uses_the_configured_node_id_once_registered():
    configured = uuid.uuid4()

    with override_settings(NODE_ID=str(configured)):
        assert get_current_node_id() == configured
