import os

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academics.demo import seed_academics_demo
from accounts.demo import DemoSeedError, seed_demo_data
from petitions.demo import seed_petitions_demo
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
                today = timezone.localdate()
                summary = seed_demo_data(password)
                s = seed_schedule_demo(today)
                a = seed_academics_demo(today)
                p = seed_petitions_demo(today)
        except DemoSeedError as exc:
            raise CommandError(str(exc)) from None
        except ValidationError as exc:
            raise CommandError(
                "Demo data conflicts with existing data: " + " ".join(exc.messages)
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
        self.stdout.write(
            self.style.SUCCESS(
                f"Academics ready: {a.terms} terms, {a.curriculum_items} curriculum items, "
                f"{a.results} final results, {a.marks} marks, {a.attendance} attendance records."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Requests ready: {p.types} types, {p.petitions} requests, "
                f"{p.attachments} attachments."
            )
        )
