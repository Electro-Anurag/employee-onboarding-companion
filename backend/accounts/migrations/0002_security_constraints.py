from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('accounts','0001_initial')]
    operations=[
        migrations.AddConstraint(model_name='membership',
            constraint=models.UniqueConstraint(fields=['user'],condition=models.Q(active=True),name='one_active_membership_per_user')),
        migrations.AddConstraint(model_name='membership',
            constraint=models.CheckConstraint(condition=models.Q(role__in=['EMPLOYEE','HR','IT','MANAGER']),name='membership_known_role')),
        migrations.AddConstraint(model_name='onetimetoken',
            constraint=models.UniqueConstraint(fields=['user','purpose'],condition=models.Q(used_at__isnull=True),name='one_pending_token_per_purpose')),
        migrations.AddConstraint(model_name='onetimetoken',
            constraint=models.CheckConstraint(condition=models.Q(purpose__in=['INVITE','RESET']),name='credential_known_purpose')),
    ]
