"""Regras de negócio e transações da app `admin_panel`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.

RF-.../9.1 (issue #144): exportação completa dos dados pessoais de um
titular (Lei 22/11 -- direito de acesso/rectificação). `Funcionário`
(RH) fica de fora por agora: o módulo `hr` ainda não tem modelos (M3) --
ver `apps/audit/signals.py`'s mesmo raciocínio para `Pagamento`.
"""

import json

from django.core import serializers


def _serialize(instance) -> dict:
    """Todos os campos concretos de `instance`, tal como já usado por
    `apps.sync.signals._write_change_record` para o mesmo efeito --
    genérico (introspecta o modelo em si, sem lista de campos mantida à
    mão aqui), por isso continua correcto mesmo que o modelo ganhe campos
    novos no futuro."""
    row = json.loads(serializers.serialize("json", [instance]))[0]
    return {"id": str(instance.pk), **row["fields"]}


def export_student_personal_data(student) -> dict:
    """Todos os dados pessoais que o FenixSchool guarda sobre `student`:
    o seu próprio perfil, os Encarregados de Educação ligados, o histórico
    de matrículas, notas e presenças."""
    from apps.attendance.models import Attendance
    from apps.enrollment.models import Enrollment
    from apps.grading.models import FinalGrade, Grade

    guardians = [
        {
            "is_primary": link.is_primary,
            "financially_responsible": link.financially_responsible,
            **_serialize(link.guardian),
        }
        for link in student.guardian_links.select_related("guardian").all()
    ]

    return {
        "aluno": _serialize(student),
        "encarregados_de_educacao": guardians,
        "matriculas": [_serialize(e) for e in Enrollment.objects.filter(student=student)],
        "notas": [_serialize(g) for g in Grade.objects.filter(student=student)],
        "medias_finais": [
            _serialize(g) for g in FinalGrade.objects.filter(enrollment__student=student)
        ],
        "presencas": [_serialize(a) for a in Attendance.objects.filter(student=student)],
    }


def export_guardian_personal_data(guardian) -> dict:
    """Todos os dados pessoais que o FenixSchool guarda sobre `guardian`:
    o seu próprio perfil e a identificação (não o perfil completo -- essa é
    o âmbito do próprio pedido do aluno) dos alunos pelos quais é
    responsável."""
    students = [
        {
            "aluno_id": str(link.student_id),
            "numero_de_aluno": link.student.student_number,
            "nome": str(link.student),
            "is_primary": link.is_primary,
            "financially_responsible": link.financially_responsible,
        }
        for link in guardian.student_links.select_related("student").all()
    ]

    return {
        "encarregado_de_educacao": _serialize(guardian),
        "alunos_associados": students,
    }
