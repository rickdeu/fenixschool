"""Regras de negócio e transações da app `guardian_portal`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.

RF-MAT-12 (issue #52): um único login dá acesso a todos os educandos do
Encarregado de Educação, com um selector de educando quando tiver mais de um.
"""

from apps.enrollment.services import get_students_for_guardian

SELECTED_STUDENT_SESSION_KEY = "guardian_selected_student_id"


def get_own_students(user):
    """All of `user`'s own educandos (issue #29's `for_guardian` scoping),
    materialized as a list -- the portal always needs the full set (to
    build the selector, to know whether one exists at all), never just an
    unevaluated queryset."""
    return list(get_students_for_guardian(user))


def resolve_selected_student(request, students):
    """Which of `students` the portal should currently show for this
    session -- the sole one, if there's only one (RF-MAT-12: no selector at
    all in that case); otherwise whichever was last picked via the
    selector, if that pick is still one of `students`; otherwise `None`
    (the selector must be shown, nothing chosen yet).
    """
    if len(students) == 1:
        return students[0]

    selected_id = request.session.get(SELECTED_STUDENT_SESSION_KEY)
    if not selected_id:
        return None
    return next((student for student in students if str(student.id) == selected_id), None)


def set_selected_student(request, student) -> None:
    request.session[SELECTED_STUDENT_SESSION_KEY] = str(student.id)
