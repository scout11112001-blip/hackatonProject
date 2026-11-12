import os

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.demo import DemoSeedError, seed_demo_data
from schedule.demo import seed_schedule_demo


class Command(BaseCommand):
    help = "Create or update fictional demo data. Password comes from DEMO_PASSWORD."

    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD", "")
        if not password:
            raise CommandError(
                "DEMO_PASSWORD environment variable is required. Set it in .env or the environment."
            )
        try:
            with transaction.atomic():
                summary = seed_demo_data(password)
                s = seed_schedule_demo(timezone.localdate())
        except DemoSeedError as exc:
            raise CommandError(str(exc)) from None
        except ValidationError as exc:
            raise CommandError(
                "Schedule demo data conflicts with existing data: " + " ".join(exc.messages)
            ) from None
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {summary.faculties} faculties, {summary.programs} programs, "
                f"{summary.groups} groups, {summary.students} students, {summary.staff} staff."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Schedule ready: {s.rooms} rooms, {s.teachers} teachers, "
                f"{s.disciplines} disciplines, {s.weekly_lessons} weekly lessons, "
                f"{s.changes} changes."
            )
        )
