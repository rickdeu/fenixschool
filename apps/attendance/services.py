"""Regras de negócio e transações da app `attendance`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from apps.academic.models import Schedule
from apps.enrollment.models import Enrollment

from .models import Attendance


class DocenteNaoAssociadoError(Exception):
    """RF-FREQ-01's RBAC acceptance criterion: apenas o docente
    efectivamente associado (`academic.Schedule.teacher`) a esse horário
    pode marcar presenças para ele -- não qualquer utilizador com perfil
    Docente/Diretor de Turma na instituição."""

    def __init__(self, teacher, schedule):
        self.teacher = teacher
        self.schedule = schedule
        super().__init__(f'"{teacher}" não está associado ao horário "{schedule}".')


def _validate_teacher_is_scheduled(*, teacher, schedule) -> None:
    # Super Administrador bypassa isto também ("acesso a tudo, sem
    # restrição alguma") -- mesmo raciocínio de
    # `grading.services._validate_teacher_is_scheduled`.
    if teacher.is_superuser:
        return
    if schedule.teacher_id != teacher.id:
        raise DocenteNaoAssociadoError(teacher, schedule)


def get_docente_schedule_slots(teacher):
    """Os horários que `teacher` pode marcar presença (issue #66) -- para
    um Docente/Diretor de Turma real, só os seus próprios
    (`academic.Schedule.teacher`); para um Super Administrador, todos os
    da instituição (nunca está de facto agendado para nada, "acesso a
    tudo")."""
    if teacher.is_superuser:
        return Schedule.all_objects.filter(institution_id=teacher.institution_id).select_related(
            "school_class", "subject"
        )
    return Schedule.all_objects.filter(teacher=teacher).select_related("school_class", "subject")


def registar_presencas(*, teacher, schedule, date, statuses: dict, origin_node_id) -> list:
    """ "Marcação de turma inteira em poucos cliques" (issue #66,
    RF-FREQ-01): `statuses` é um mapa `{enrollment_id: Attendance.Status}`
    -- uma só chamada marca a turma toda de uma vez. Idempotente: uma
    presença já registada para o mesmo (matrícula, horário, data) é
    actualizada em vez de duplicada, mesmo raciocínio de
    `grading.services.lancar_ou_atualizar_nota`.
    """
    _validate_teacher_is_scheduled(teacher=teacher, schedule=schedule)

    enrollments_by_id = {
        str(enrollment.id): enrollment
        for enrollment in Enrollment.all_objects.filter(
            institution_id=schedule.institution_id, id__in=statuses.keys()
        ).select_related("student")
    }

    existing_by_enrollment_id = {
        attendance.enrollment_id: attendance
        for attendance in Attendance.all_objects.filter(
            institution_id=schedule.institution_id, schedule=schedule, date=date
        )
    }

    results = []
    for enrollment_id, status in statuses.items():
        enrollment = enrollments_by_id.get(enrollment_id)
        if enrollment is None:
            continue

        existing = existing_by_enrollment_id.get(enrollment.id)
        if existing is not None:
            existing.status = status
            existing.registered_by = teacher
            existing.save()
            results.append(existing)
        else:
            results.append(
                Attendance.objects.create(
                    institution=schedule.institution,
                    origin_node_id=origin_node_id,
                    student=enrollment.student,
                    enrollment=enrollment,
                    schedule=schedule,
                    date=date,
                    status=status,
                    registered_by=teacher,
                )
            )
    return results


class EstadoInvalidoParaJustificacaoError(Exception):
    """RF-FREQ-02: só uma Falta (ou uma Falta Justificada, para corrigir/
    substituir uma justificação já registada) pode ser justificada -- não
    faz sentido "justificar" uma Presença."""

    def __init__(self, attendance):
        self.attendance = attendance
        super().__init__(
            f'"{attendance}" não é uma falta -- só uma falta pode ser justificada.'
        )


def justificar_falta(*, attendance: Attendance, text: str, justified_by, attachment=None):
    """ "Justificação de faltas com anexo opcional" (issue #67, RF-FREQ-02):
    muda o estado para Falta Justificada e regista o texto/anexo. `attachment`
    é opcional (`None` por omissão) -- o critério de aceitação exige que a
    justificação seja registável com ou sem ele."""

    if attendance.status not in (Attendance.Status.ABSENT, Attendance.Status.JUSTIFIED_ABSENT):
        raise EstadoInvalidoParaJustificacaoError(attendance)

    attendance.status = Attendance.Status.JUSTIFIED_ABSENT
    attendance.justification_text = text
    if attachment is not None:
        attendance.justification_attachment = attachment
    attendance.registered_by = justified_by
    attendance.save()
    return attendance
