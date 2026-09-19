"""Regras de negócio e transações da app `attendance`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from decimal import Decimal

from apps.academic.models import Schedule, Subject
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


# RF-FREQ-03's próprio exemplo de implementação: "limite_faltas = 3 *
# carga_horaria_semanal". Tal como `Institution.max_recoverable_subjects`,
# não é um valor normativo confirmado junto do Decreto Presidencial 162/23
# (docs/legislacao/README.md) -- fica hardcoded como ponto de partida até a
# issue #175 o tornar configurável por instituição.
ABSENCE_LIMIT_WEEKLY_LOAD_MULTIPLIER = Decimal("3")


def _schedule_duration_hours(schedule) -> Decimal:
    start_minutes = schedule.start_time.hour * 60 + schedule.start_time.minute
    end_minutes = schedule.end_time.hour * 60 + schedule.end_time.minute
    return Decimal(end_minutes - start_minutes) / Decimal(60)


def calcular_assiduidade(*, enrollment, subject, academic_term=None) -> dict:
    """ "Cálculo de percentagem de assiduidade e alerta de limite legal"
    (issue #68, RF-FREQ-03): acumula as horas de falta (justificadas e
    injustificadas) de `enrollment` em `subject` -- todo o ano lectivo por
    omissão, ou só `academic_term` quando indicado -- e compara-as com
    `limite_faltas = 3 × carga_horária_semanal` (`Subject.weekly_hours`).

    Só as faltas **injustificadas** contam para o limite legal (uma falta
    justificada não deveria penalizar o aluno) -- ambas contam para a
    percentagem de assiduidade em si (fisicamente, o aluno não esteve
    presente de qualquer forma). Nenhuma aula registada ainda (`total_hours
    == 0`) devolve 100% de assiduidade, sem risco -- não uma divisão por
    zero nem um falso alerta.
    """
    records = Attendance.all_objects.filter(
        institution_id=enrollment.institution_id, enrollment=enrollment, schedule__subject=subject
    ).select_related("schedule")
    if academic_term is not None:
        records = records.filter(
            date__gte=academic_term.start_date, date__lte=academic_term.end_date
        )

    total_hours = Decimal("0")
    absence_hours = Decimal("0")
    unjustified_absence_hours = Decimal("0")
    for record in records:
        duration = _schedule_duration_hours(record.schedule)
        total_hours += duration
        if record.status in (Attendance.Status.ABSENT, Attendance.Status.JUSTIFIED_ABSENT):
            absence_hours += duration
        if record.status == Attendance.Status.ABSENT:
            unjustified_absence_hours += duration

    attendance_percentage = (
        (total_hours - absence_hours) / total_hours * Decimal("100")
        if total_hours > 0
        else Decimal("100")
    )
    limit_hours = ABSENCE_LIMIT_WEEKLY_LOAD_MULTIPLIER * Decimal(subject.weekly_hours)

    return {
        "total_hours": total_hours,
        "absence_hours": absence_hours,
        "unjustified_absence_hours": unjustified_absence_hours,
        "attendance_percentage": attendance_percentage.quantize(Decimal("0.1")),
        "limit_hours": limit_hours,
        "exceeds_limit": unjustified_absence_hours > limit_hours,
    }


def mapa_faltas_aluno(*, enrollment) -> dict:
    """A assiduidade agregada de `enrollment` em todas as disciplinas do
    seu ano curricular -- o resumo de uma linha do "mapa de faltas" (issue
    #69, RF-FREQ-04), reutilizado tanto pelo mapa por turma
    (`mapa_faltas_turma`) como pela vista do Encarregado de Educação
    (`guardian_portal`)."""
    subjects = Subject.objects.filter(
        institution=enrollment.institution, curricular_year=enrollment.curricular_year
    )
    total_hours = Decimal("0")
    absence_hours = Decimal("0")
    unjustified_absence_hours = Decimal("0")
    at_risk_subjects = []
    for subject in subjects:
        result = calcular_assiduidade(enrollment=enrollment, subject=subject)
        total_hours += result["total_hours"]
        absence_hours += result["absence_hours"]
        unjustified_absence_hours += result["unjustified_absence_hours"]
        if result["exceeds_limit"]:
            at_risk_subjects.append(subject)

    attendance_percentage = (
        (total_hours - absence_hours) / total_hours * Decimal("100")
        if total_hours > 0
        else Decimal("100")
    )
    return {
        "enrollment": enrollment,
        "total_hours": total_hours,
        "unjustified_absence_hours": unjustified_absence_hours,
        "attendance_percentage": attendance_percentage.quantize(Decimal("0.1")),
        "at_risk_subjects": at_risk_subjects,
    }


def mapa_faltas_turma(*, institution, school_class) -> list[dict]:
    """ "Mapa de faltas por turma" (issue #69, RF-FREQ-04): uma linha por
    aluno matriculado em `school_class`, com a assiduidade agregada de
    `mapa_faltas_aluno` -- visão geral da turma, não o detalhe por
    disciplina (`calcular_assiduidade`)."""
    enrollments = (
        Enrollment.objects.filter(
            institution=institution,
            school_class=school_class,
            status__in=[Enrollment.Status.PENDING, Enrollment.Status.ACTIVE],
        )
        .select_related("student", "curricular_year")
        .order_by("student__first_name", "student__last_name")
    )
    return [mapa_faltas_aluno(enrollment=enrollment) for enrollment in enrollments]
