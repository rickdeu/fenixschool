"""Views da app `core`."""

from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from .forms import InstitutionSetupForm, ManagerSetupForm
from .models import Institution
from .services import setup_institution


class SetupWizardView(View):
    """First-run setup wizard (issue #17, docs/04-arquitetura-tecnica.md §4.4.2):
    creates the Institution and its first user (the Manager) in one
    transaction. Accessible only while no Institution exists yet on this
    node -- once one does (including right after this view itself creates
    one), every request redirects away instead.

    Redirects to the Django Admin's own login (`admin:login`) rather than a
    dedicated login page, since issue #24 ("Login sem seleção de escola")
    hasn't built one yet.
    """

    template_name = "core/setup_wizard.html"

    def dispatch(self, request, *args, **kwargs):
        if Institution.objects.exists():
            return redirect(reverse("admin:login"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "institution_form": InstitutionSetupForm(),
                "manager_form": ManagerSetupForm(),
            },
        )

    def post(self, request):
        institution_form = InstitutionSetupForm(request.POST)
        manager_form = ManagerSetupForm(request.POST)

        if institution_form.is_valid() and manager_form.is_valid():
            setup_institution(
                institution_data=institution_form.cleaned_data,
                manager_data={
                    "username": manager_form.cleaned_data["username"],
                    "email": manager_form.cleaned_data["email"],
                    "first_name": manager_form.cleaned_data["first_name"],
                    "last_name": manager_form.cleaned_data["last_name"],
                    "phone": manager_form.cleaned_data["phone"],
                    "password": manager_form.cleaned_data["password"],
                },
            )
            return redirect(reverse("admin:login"))

        return render(
            request,
            self.template_name,
            {"institution_form": institution_form, "manager_form": manager_form},
        )
