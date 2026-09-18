"""Regras de negócio e transações da app `accounts`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import Profile, User

# Where each profile lands right after login/2FA verification (issue #24's
# "redireciona ao dashboard correcto consoante o perfil"). Profiles whose own
# portal/dashboard doesn't exist yet (issues #105, #109, #119, ...) land on
# the placeholder below instead of a fabricated one -- add/replace entries
# here as each lands, rather than guessing at URLs that don't exist yet.
PROFILE_LANDING_URL_NAMES = {
    Profile.SUPER_ADMIN: "admin:index",
    Profile.INSTITUTION_ADMIN: "admin:index",
    Profile.PEDAGOGICAL_DIRECTION: "admin:index",
    Profile.SECRETARY: "admin:index",
    Profile.FINANCE: "admin:index",
    Profile.HR: "admin:index",
}


def get_login_redirect_url_name(user: User) -> str:
    """Where to send `user` once they're fully logged in (2FA included, for
    the profiles that require it)."""
    return PROFILE_LANDING_URL_NAMES.get(user.profile, "accounts:landing_placeholder")


# -- 2FA (TOTP) -- issue #25, RNF-SEC-05, docs/09-seguranca-e-privacidade.md §9.2

MANDATORY_2FA_PROFILES = {Profile.SUPER_ADMIN, Profile.INSTITUTION_ADMIN, Profile.FINANCE}


def requires_two_factor(user: User) -> bool:
    """Whether `user`'s profile is one of the 3 RNF-SEC-05 lists as
    high-risk (Super Administrador/Administrador da Instituição/
    Financeiro-Tesouraria) -- 2FA is mandatory for these, optional (not
    enforced) for everyone else."""
    return user.profile in MANDATORY_2FA_PROFILES


def user_has_confirmed_totp_device(user: User) -> bool:
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def get_two_factor_redirect_url_name(user: User) -> str:
    """Where to send a `user` who still needs to complete 2FA: straight to
    entering a code if they already have a confirmed device (a returning
    login), or to the QR-code enrolment flow otherwise (their very first
    time)."""
    return (
        "accounts:two_factor_verify"
        if user_has_confirmed_totp_device(user)
        else "accounts:two_factor_setup"
    )


def create_user(*, created_by: User, institution=None, **fields) -> User:
    """Create a `User`, propagating the tenant automatically (issue #23,
    docs/04-arquitetura-tecnica.md §4.4.1).

    The Super Administrator is the **only** profile that picks `institution`
    explicitly -- every other creator's new user always inherits
    `created_by.institution`, regardless of what (if anything) is passed as
    `institution`, so an ordinary "register a colleague" form never even
    needs an "Escola" field to begin with.
    """
    if created_by.is_super_admin:
        if institution is None:
            raise ValueError("institution is required when created_by is a Super Administrator.")
    else:
        institution = created_by.institution

    return User.objects.create_user(
        institution=institution,
        created_by=created_by,
        **fields,
    )
