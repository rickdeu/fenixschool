"""Vista principal do portal do encarregado (issue #52, RF-MAT-12)."""

from django.shortcuts import redirect, render

from ..forms import StudentSelectorForm
from ..permissions import guardian_required
from ..services import get_own_students, resolve_selected_student, set_selected_student


@guardian_required
def dashboard_view(request):
    students = get_own_students(request.user)
    selected_student = resolve_selected_student(request, students)
    selector_form = None

    if len(students) > 1:
        if request.method == "POST":
            selector_form = StudentSelectorForm(request.POST, students=students)
            if selector_form.is_valid():
                selected_id = selector_form.cleaned_data["student"]
                selected_student = next(s for s in students if str(s.id) == selected_id)
                set_selected_student(request, selected_student)
                return redirect("guardian_portal:dashboard")
        else:
            initial = {"student": str(selected_student.id)} if selected_student else None
            selector_form = StudentSelectorForm(students=students, initial=initial)

    return render(
        request,
        "guardian_portal/dashboard.html",
        {
            "students": students,
            "selected_student": selected_student,
            "selector_form": selector_form,
        },
    )
