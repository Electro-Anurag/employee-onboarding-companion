import uuid
import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="FoundationOperation", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("label", models.CharField(max_length=128)),
            ("status", models.CharField(default="CREATED", max_length=16)),
            ("crash_after_apply_once", models.BooleanField(default=False)),
            ("crash_fired", models.BooleanField(default=False)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("applied_at", models.DateTimeField(null=True)),
        ]),
        migrations.CreateModel(name="FoundationEffect", fields=[
            ("operation", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to="foundation.foundationoperation")),
            ("applied_at", models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name="FoundationAudit", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("event", models.CharField(max_length=20)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("operation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="foundation.foundationoperation")),
        ]),
        migrations.AddConstraint(model_name="foundationaudit", constraint=models.UniqueConstraint(fields=("operation", "event"), name="m0_unique_operation_event")),
    ]
