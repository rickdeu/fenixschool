"""Post-login landing page (issue #24) -- a real per-profile "Tarefas Actuais"
dashboard (issue #119) for whichever pendências already have a real screen to
act on, plus an honest "not built yet" fallback for the profiles that don't.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.accounts.models import Profile
from apps.enrollment.models import Candidate, Student


def _pending_tasks(request):
    """Each widget is gated by the permission its target screen itself
    requires, not by `request.user.profile` -- whichever profiles a future
    RBAC change grants that permission to will see the matching widget
    automatically, without this view having to be kept in sync by hand.
    """
    widgets = []

    if request.user.has_perm("enrollment.view_candidate"):
        count = Candidate.objects.filter(status=Candidate.Status.PENDING).count()
        widgets.append(
            {
                "title": "Candidaturas por processar",
                "count": count,
                "url": reverse("enrollment:candidate_list"),
                "icon": "bi-person-lines-fill",
            }
        )

    if request.user.has_perm("enrollment.add_enrollment"):
        count = Student.objects.filter(
            admitted_from_candidate__isnull=False, enrollments__isnull=True
        ).count()
        widgets.append(
            {
                "title": "Alunos admitidos por matricular",
                "count": count,
                "url": reverse("enrollment:bulk_enrollment"),
                "icon": "bi-journal-check",
            }
        )

    return widgets


@login_required
def landing_placeholder(request):
    if request.user.profile == Profile.GUARDIAN:
        return redirect("guardian_portal:dashboard")

    return render(
        request, "accounts/landing_placeholder.html", {"widgets": _pending_tasks(request)}
    )
