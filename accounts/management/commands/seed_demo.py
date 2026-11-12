import os

from django.core.management.base import BaseCommand, CommandError

from accounts.demo import DemoSeedError, seed_demo_data


class Command(BaseCommand):
    help = "Create or update fictional demo data. Password comes from DEMO_PASSWORD."

    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD", "")
        if not password:
            raise CommandError(
                "DEMO_PASSWORD environment variable is required. Set it in .env or the environment."
            )
        try:
            summary = seed_demo_data(password)
        except DemoSeedError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {summary.faculties} faculties, {summary.programs} programs, "
                f"{summary.groups} groups, {summary.students} students, {summary.staff} staff."
            )
        )
