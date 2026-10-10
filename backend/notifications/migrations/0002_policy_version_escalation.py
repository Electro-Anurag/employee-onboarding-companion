"""Additive immutable identity dimension for versioned M5 escalation rules."""
from django.db import migrations,models


class Migration(migrations.Migration):
    dependencies=[('notifications','0001_initial')]
    operations=[
        migrations.AddField(model_name='reminderintent',name='policy_version',
            field=models.CharField(max_length=32,default='M5-REMIND-V1')),
        migrations.RemoveConstraint(model_name='reminderintent',
            name='m5_unique_task_reminder_identity'),
        migrations.AddConstraint(model_name='reminderintent',
            constraint=models.UniqueConstraint(
                fields=['subject_type','task','schedule_revision',
                        'action_revision','recipient','rule_code','time_bucket',
                        'policy_version'],name='m5_unique_task_reminder_identity')),
    ]
