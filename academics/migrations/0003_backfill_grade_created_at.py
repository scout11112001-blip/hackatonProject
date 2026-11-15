from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db import migrations
from django.utils import timezone

MOSCOW = ZoneInfo("Europe/Moscow")


def backfill(apps, schema_editor):
    now = timezone.now()
    for model_name in ("CurrentMark", "FinalResult"):
        model = apps.get_model("academics", model_name)
        rows = list(model.objects.only("pk", "date", "created_at"))
        for row in rows:
            recorded = min(datetime.combine(row.date, time(18, 0), tzinfo=MOSCOW), now)
            row.created_at = min(recorded, row.created_at)
        model.objects.bulk_update(rows, ["created_at"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [("academics", "0002_currentmark_created_at_alter_finalresult_created_at")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
