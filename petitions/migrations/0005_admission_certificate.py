"""TASK-017: "Справка в военкомат" becomes "Справка о поступлении" (rename in place)."""

from django.db import migrations

OLD = {
    "name": "Справка в военкомат",
    "comment_required": True,
    "comment_hint": "Укажите военкомат.",
    "description": "Справка для военного комиссариата.",
}
NEW = {
    "name": "Справка о поступлении",
    "comment_required": False,
    "comment_hint": "Можно указать, куда нужна справка.",
    "description": "Подтверждает зачисление в университет.",
}


def _rename(apps, source: dict, target: dict) -> None:
    RequestType = apps.get_model("petitions", "RequestType")
    row = RequestType.objects.filter(name=source["name"]).first()
    if row is None:
        return
    if RequestType.objects.filter(name=target["name"]).exists():
        # The target name is taken (created by hand): hide the source type instead.
        row.is_active = False
        row.save(update_fields=["is_active"])
        return
    for field, value in target.items():
        setattr(row, field, value)
    row.kind = "certificate"
    row.processing_days = 3
    row.subject_required = False
    row.save()


def forwards(apps, schema_editor):
    _rename(apps, OLD, NEW)


def backwards(apps, schema_editor):
    _rename(apps, NEW, OLD)


class Migration(migrations.Migration):
    dependencies = [("petitions", "0004_documents_wording")]

    operations = [migrations.RunPython(forwards, backwards)]
