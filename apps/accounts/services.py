"""Regras de negócio e transações da app `accounts`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
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
    Profile.GUARDIAN: "guardian_portal:dashboard",
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


# -- Bloqueio progressivo de conta -- issue #26, RNF-SEC-02,
# docs/09-seguranca-e-privacidade.md §9.2

MAX_FAILED_LOGIN_ATTEMPTS = 5
BASE_LOCKOUT_MINUTES = 1
LOCKOUT_BACKOFF_FACTOR = 2
MAX_LOCKOUT_MINUTES = 60


def lockout_duration_minutes(lockout_count: int) -> int:
    """Each further lockout is twice as long as the last one (progressive
    back-off), capped so a legitimate user already locked out several
    times in a row is never shut out for an unreasonable amount of time."""
    return min(BASE_LOCKOUT_MINUTES * (LOCKOUT_BACKOFF_FACTOR**lockout_count), MAX_LOCKOUT_MINUTES)


def register_failed_login(user: User) -> None:
    """Called once per failed login attempt for a *known* user. A no-op
    while already locked -- otherwise repeated attempts during an active
    lockout would keep extending it indefinitely, since a locked account
    also fails to authenticate on every further attempt.
    """
    if user.is_locked:
        return

    user.failed_login_attempts += 1
    if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = timezone.now() + timedelta(
            minutes=lockout_duration_minutes(user.lockout_count)
        )
        user.lockout_count += 1
        user.failed_login_attempts = 0
    user.save(update_fields=["failed_login_attempts", "locked_until", "lockout_count"])


def reset_lockout_state(user: User) -> None:
    """Called on every successful login -- proves the account is back in
    its owner's hands, so past failures no longer count against it."""
    if user.failed_login_attempts or user.locked_until or user.lockout_count:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.lockout_count = 0
        user.save(update_fields=["failed_login_attempts", "locked_until", "lockout_count"])


# -- Expiração de sessão por inactividade -- issue #27, docs/09-seguranca-e-
# privacidade.md §9.2


def get_session_timeout_seconds(user: User) -> int:
    """How long `user`'s session may sit idle before expiring, in seconds --
    shorter for higher-risk/shared-workstation profiles (see
    `settings.SESSION_TIMEOUT_MINUTES_BY_PROFILE`'s own comment for the
    reasoning behind each value)."""
    minutes = settings.SESSION_TIMEOUT_MINUTES_BY_PROFILE.get(
        user.profile, settings.DEFAULT_SESSION_TIMEOUT_MINUTES
    )
    return minutes * 60


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
