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
