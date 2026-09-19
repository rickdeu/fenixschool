"""Filtros para renderizar formulários com classes Bootstrap (issue #187),
sem reescrever `widget=` em cada campo de cada formulário do projecto.
"""

from django import template

register = template.Library()


@register.filter(name="add_class")
def add_class(field, css_class):
    """Renders `field` with `css_class` appended to its widget's own
    `class` attribute -- never replacing whatever it already had."""
    existing = field.field.widget.attrs.get("class", "")
    classes = f"{existing} {css_class}".strip()
    return field.as_widget(attrs={**field.field.widget.attrs, "class": classes})


@register.filter(name="widget_type")
def widget_type(field):
    """The field's widget class name, lowercased (e.g. "textinput",
    "select", "checkboxinput") -- lets a template pick the right Bootstrap
    markup (`form-control`/`form-select`/`form-check`) per field without
    the form itself having to say so."""
    return field.field.widget.__class__.__name__.lower()


@register.inclusion_tag("components/choice_field.html")
def choice_field(
    name, queryset, selected=None, label=None, label_attr=None, multiple=False, required=False
):
    """Renders `queryset` as radios (single choice) or checkboxes (`multiple=True`)
    when it has 4 or fewer options, or as a `<select>` otherwise (feedback do
    utilizador: "onde tem select, para página onde no máximo 4 campos... deve
    ser sempre um check") -- one plain GET-param filter field, not a Django
    `Form` field (see `components/bootstrap_form.html` for those).

    `label_attr`: the attribute to read each option's display text from
    (e.g. "designation"/"name"); falls back to `str(obj)` when omitted (e.g.
    for `AcademicTerm`, whose own `__str__` already reads as "1.º Trimestre
    — 2026/2027").
    """
    options = [
        (obj.pk, getattr(obj, label_attr) if label_attr else str(obj)) for obj in queryset
    ]

    if multiple:
        selected_values = selected or []
    else:
        selected_values = [selected] if selected else []
    selected_values = {str(value) for value in selected_values if value}

    return {
        "name": name,
        "options": options,
        "selected_values": selected_values,
        "label": label,
        "multiple": multiple,
        "required": required,
        "use_choices": len(options) <= 4,
    }
