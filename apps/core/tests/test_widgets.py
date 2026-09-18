"""Tests for `apps.core.widgets.MunicipalitySelect` -- the province→município
cascade filter in `static/js/app.js` relies on every município `<option>`
carrying its own `data-province` attribute."""

import pytest

from apps.core.forms import InstitutionEditForm
from apps.core.models import Municipality, Province

pytestmark = pytest.mark.django_db


def test_every_municipality_option_is_tagged_with_its_province():
    huila = Province.objects.get(pk="huila")
    lubango = Municipality.objects.get(pk="huila-lubango")

    form = InstitutionEditForm()
    rendered = str(form["municipality"])

    assert f'data-province="{huila.pk}"' in rendered
    assert f'value="{lubango.pk}"' in rendered
