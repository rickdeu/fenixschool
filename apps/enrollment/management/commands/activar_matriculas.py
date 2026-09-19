"""Manual trigger for
`apps.enrollment.services.activar_matriculas_do_ano_lectivo_em_curso` -- the
same activation the daily Django-Q2 schedule already runs automatically."""

from django.core.management.base import BaseCommand

from apps.enrollment.services import activar_matriculas_do_ano_lectivo_em_curso


class Command(BaseCommand):
    help = "Activa (Pendente -> Activa) toda matrícula cujo Ano Lectivo já começou."

    def handle(self, *args, **options):
        count = activar_matriculas_do_ano_lectivo_em_curso()
        self.stdout.write(self.style.SUCCESS(f"{count} matrícula(s) activada(s)."))
