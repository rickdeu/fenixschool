"""View de destino pós-login para perfis sem painel próprio ainda (issue #24)."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def landing_placeholder(request):
    """Post-login landing page for profiles without their own dashboard yet
    (Docente, Diretor de Turma, Biblioteca, Encarregado de Educação, Aluno --
    see issues #105, #109, #119). Deliberately not a fabricated dashboard:
    just an honest "you're signed in, this area isn't built yet" page.
    """
    return render(request, "accounts/landing_placeholder.html")
