"""`factory_boy` factory for `accounts.User` — see docs/13-testes-e-qualidade.md §13.1.

`User.profile` is left as a plain constructor argument (rather than one factory
subclass per profile in `docs/07-perfis-permissoes-e-fluxos.md` §7.1) so tests ask
for exactly the profile/institution combination they need, e.g.
``UserFactory(profile=Profile.TEACHER, institution=institution)`` — see the
``user_factory`` fixture in the repository's root `conftest.py`.
"""

import factory
from factory.django import DjangoModelFactory

from .models import Profile, User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    profile = Profile.INSTITUTION_ADMIN
    institution = None
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "Test-Password-123")
        if create:
            self.save(update_fields=["password"])
