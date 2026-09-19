"""Signals da app `enrollment`."""

from django.apps import apps as django_apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def schedule_enrollment_activation(sender, **kwargs):
    """Regista a activação diária de matrículas (Pendente -> Activa quando
    o Ano Lectivo começa, ver
    `apps.enrollment.services.activar_matriculas_do_ano_lectivo_em_curso`)
    como agendamento do Django-Q2 -- mesmo padrão/razão de
    `apps.core.signals.schedule_automatic_backup`, incl. só existir no Nó
    Local (`django_q` só está instalado aí)."""
    if not django_apps.is_installed("django_q"):
        return

    from django_q.models import Schedule

    Schedule.objects.get_or_create(
        func="apps.enrollment.services.activar_matriculas_do_ano_lectivo_em_curso",
        defaults={
            "name": "Activação diária de matrículas do ano lectivo em curso",
            "schedule_type": Schedule.DAILY,
        },
    )
