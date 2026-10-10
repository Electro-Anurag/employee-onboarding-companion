# M5: forward-only durable in-app reminder identity and recipient inbox.
import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('accounts','0002_security_constraints'),
        ('onboarding','0020_audit_existing_manager_completion_provenance'),
    ]
    operations = [
        migrations.CreateModel(
            name='ReminderIntent',
            fields=[
                ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
                ('subject_type',models.CharField(default='TASK',max_length=16)),
                ('schedule_revision',models.PositiveBigIntegerField(default=0)),
                ('action_revision',models.PositiveBigIntegerField()),
                ('rule_code',models.CharField(max_length=32)),
                ('time_bucket',models.CharField(max_length=40)),
                ('due_at',models.DateTimeField()),
                ('status',models.CharField(max_length=16,default='DELIVERED',
                    choices=[(v,v) for v in ('DELIVERED','SUPERSEDED','SUPPRESSED')])),
                ('created_at',models.DateTimeField(default=django.utils.timezone.now)),
                ('case',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='onboarding.onboardingcase')),
                ('task',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='onboarding.task')),
                ('recipient',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
            ],
            options={'indexes':[models.Index(fields=['case','status'],name='m5_reminder_case_status')]},
        ),
        migrations.AddConstraint(
            model_name='reminderintent',
            constraint=models.UniqueConstraint(
                fields=['subject_type','task','schedule_revision','action_revision',
                        'recipient','rule_code','time_bucket'],
                name='m5_unique_task_reminder_identity'),
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
                ('summary',models.CharField(max_length=200)),
                ('status',models.CharField(max_length=16,default='ACTIVE',
                    choices=[(v,v) for v in ('ACTIVE','RESOLVED','SUPERSEDED')])),
                ('created_at',models.DateTimeField(default=django.utils.timezone.now)),
                ('read_at',models.DateTimeField(null=True)),
                ('case',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='onboarding.onboardingcase')),
                ('intent',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,to='notifications.reminderintent')),
                ('recipient',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='accounts.user')),
                ('task',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='onboarding.task')),
            ],
            options={'indexes':[models.Index(fields=['recipient','created_at'],name='m5_inbox_recipient_date')]},
        ),
    ]
