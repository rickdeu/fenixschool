"""Vista de configuração inicial do 2FA/TOTP (issue #25, RNF-SEC-05).

Primeiro login de um perfil de alto risco (Administrador da Instituição,
Super Administrador, Financeiro/Tesouraria): gera um código QR (TOTP corre
totalmente offline -- não depende de SMS/rede) para o utilizador associar a
uma app autenticadora, e só activa o dispositivo depois de confirmar que o
utilizador conseguiu gerar um código válido com ele.
"""

import base64
from io import BytesIO

import qrcode
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from ..forms import TOTPTokenForm
from ..services import get_login_redirect_url_name


@login_required
def two_factor_setup_view(request):
    user = request.user
    if user.is_verified():
        return redirect(get_login_redirect_url_name(user))

    device, _created = TOTPDevice.objects.get_or_create(
        user=user, confirmed=False, defaults={"name": "default"}
    )

    if request.method == "POST":
        form = TOTPTokenForm(request.POST)
        if form.is_valid() and device.verify_token(form.cleaned_data["token"]):
            device.confirmed = True
            device.save(update_fields=["confirmed"])
            otp_login(request, device)
            return redirect(get_login_redirect_url_name(user))
        form.add_error("token", "Código inválido. Tente novamente.")
    else:
        form = TOTPTokenForm()

    qr_code_data_uri = _render_qr_code_data_uri(device.config_url)

    return render(
        request,
        "accounts/two_factor_setup.html",
        {
            "form": form,
            "qr_code_data_uri": qr_code_data_uri,
            "manual_entry_key": device.key,
        },
    )


def _render_qr_code_data_uri(provisioning_uri: str) -> str:
    image = qrcode.make(provisioning_uri)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
