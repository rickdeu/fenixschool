"""Regras de negócio e transações da app `academic`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from django.db.models import Q


class ScheduleConflictError(Exception):
    """RF-CURR-06 (issue #37): a new/edited Horário overlaps an existing one
    for the same docente, sala or turma, at an overlapping day/time."""

    def __init__(self, conflicting_schedule, reason: str):
        self.conflicting_schedule = conflicting_schedule
        self.reason = reason
        super().__init__(
            f'Conflito de horário: {reason} já está ocupada por "{conflicting_schedule}" '
            f"à {conflicting_schedule.get_weekday_display()}, "
            f"{conflicting_schedule.start_time}-{conflicting_schedule.end_time}."
        )


def _intervals_overlap(start_a, end_a, start_b, end_b) -> bool:
    return start_a < end_b and start_b < end_a


def validate_schedule_conflict(schedule) -> None:
    """Raises `ScheduleConflictError` if `schedule` (an `academic.Schedule`
    instance -- saved or not yet saved) overlaps an existing Schedule for
    the same docente, sala or turma, on the same day, at an overlapping
    time. `schedule.pk` being `None` (not yet saved) makes `.exclude(pk=...)`
    a no-op, which is exactly right: there is nothing yet to exclude itself
    from.
    """
    from .models import Schedule

    # `all_objects`, not `objects`: this can be called from outside any
    # ambient tenant context (e.g. a plain function call in a test, or from
    # a form's `clean()` before the request's own tenant context would
    # apply) -- `objects` would silently fail closed to an empty queryset
    # there, missing real conflicts instead of finding them.
    candidates = (
        Schedule.all_objects.filter(
            Q(teacher_id=schedule.teacher_id)
            | Q(room_id=schedule.room_id)
            | Q(school_class_id=schedule.school_class_id),
            institution_id=schedule.institution_id,
            weekday=schedule.weekday,
        )
        .exclude(pk=schedule.pk)
        .select_related("teacher", "room", "school_class")
    )

    for existing in candidates:
        if not _intervals_overlap(
            schedule.start_time, schedule.end_time, existing.start_time, existing.end_time
        ):
            continue

        if existing.teacher_id == schedule.teacher_id:
            reason = f'o docente "{existing.teacher}"'
        elif existing.room_id == schedule.room_id:
            reason = f'a sala "{existing.room}"'
        else:
            reason = f'a turma "{existing.school_class}"'
        raise ScheduleConflictError(existing, reason)
