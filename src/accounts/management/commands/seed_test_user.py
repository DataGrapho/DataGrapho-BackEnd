from __future__ import annotations

from django.core.management.base import BaseCommand

from accounts.models import Usuario


class Command(BaseCommand):
    help = "Create the default test user if it does not exist."

    def handle(self, *args, **options):
        email = "teste@datafit.com"
        password = "teste123"

        user, created = Usuario.objects.update_or_create(
            email=email,
            defaults={
                "cpf": "000.000.000-01",
                "nome": "Usuario Teste",
                "is_active": True,
            },
        )
        user.set_password(password)
        user.is_active = True
        user.save(update_fields=["password", "is_active"])

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Test user {action}: {user.email}"))
