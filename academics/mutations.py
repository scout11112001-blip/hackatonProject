"""The only write path for academics models in application code."""

from django.db import models, transaction


def save_validated(instance: models.Model) -> models.Model:
    with transaction.atomic():
        instance.full_clean()
        instance.save()
        return instance
