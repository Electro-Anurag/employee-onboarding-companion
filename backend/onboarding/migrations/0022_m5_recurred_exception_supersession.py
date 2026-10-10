"""Forward-only truthful terminal status when a resolved blocker recurs."""
from django.db import migrations,models

class Migration(migrations.Migration):
    dependencies=[('onboarding','0021_m5_exception_episodes')]
    operations=[
        migrations.RemoveConstraint(model_name='caseexception',
            name='m5_exception_valid_status'),
        migrations.AlterField(model_name='caseexception',name='status',
            field=models.CharField(max_length=12,default='OPEN',choices=[
                ('OPEN','OPEN'),('ASSIGNED','ASSIGNED'),('RESOLVED','RESOLVED'),
                ('CLOSED','CLOSED'),('SUPERSEDED','SUPERSEDED')])),
        migrations.AlterField(model_name='caseexceptionevent',name='action',
            field=models.CharField(max_length=12,choices=[
                ('OPEN','OPEN'),('ASSIGN','ASSIGN'),('RESOLVE','RESOLVE'),
                ('CLOSE','CLOSE'),('SUPERSEDE','SUPERSEDE')])),
        migrations.AddConstraint(model_name='caseexception',
            constraint=models.CheckConstraint(
                condition=models.Q(status__in=[
                    'OPEN','ASSIGNED','RESOLVED','CLOSED','SUPERSEDED']),
                name='m5_exception_valid_status')),
    ]
