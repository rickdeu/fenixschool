"""Menu "Inscrições" (issue #45/#47): ponto de entrada para os fluxos de
Inscrição e Matrícula."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index_view(request):
    return render(request, "enrollment/index.html")
