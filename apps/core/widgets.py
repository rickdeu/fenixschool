"""Widgets shared across apps' forms."""

from django import forms


class MunicipalitySelect(forms.Select):
    """Tags every `<option>` with its province (`data-province`), so
    `static/js/app.js`'s province→município cascade can filter this select's
    options client-side without a round trip: with no província selected, or
    one that doesn't match, município shows nothing to pick from.

    `value` is a `ModelChoiceIteratorValue` when this widget backs a
    `ModelChoiceField` (the normal case for a `municipality` FK field) --
    `value.instance` gives the actual `Municipality` row without an extra
    query per option, since `ModelChoiceIterator` already fetched it.
    """

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        municipality = getattr(value, "instance", None)
        if municipality is not None:
            option["attrs"]["data-province"] = municipality.province_id
        return option
