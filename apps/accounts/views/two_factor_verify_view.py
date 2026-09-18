"""Vista de verificação do 2FA/TOTP em cada novo início de sessão (issue #25,
RNF-SEC-05) -- para um utilizador que já tem um dispositivo confirmado de
uma configuração anterior."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django_otp import login as otp_login
from django_otp import match_token
from django_otp.plugins.otp_totp.models import TOTPDevice

from ..forms import TOTPTokenForm
from ..services import get_login_redirect_url_name


@login_required
def two_factor_verify_view(request):
    user = request.user
    if user.is_verified():
        return redirect(get_login_redirect_url_name(user))

    if not TOTPDevice.objects.filter(user=user, confirmed=True).exists():
        return redirect("accounts:two_factor_setup")

    if request.method == "POST":
        form = TOTPTokenForm(request.POST)
        if form.is_valid():
            device = match_token(user, form.cleaned_data["token"])
            if device is not None:
                otp_login(request, device)
                return redirect(get_login_redirect_url_name(user))
        form.add_error("token", "Código inválido. Tente novamente.")
    else:
        form = TOTPTokenForm()

    return render(request, "accounts/two_factor_verify.html", {"form": form})
