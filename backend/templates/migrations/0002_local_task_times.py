from django.db import migrations,models
class Migration(migrations.Migration):
    dependencies=[('templates','0001_initial')]
    operations=[
        migrations.AddField(model_name='templatetask',name='available_local_time',
                            field=models.CharField(max_length=5,default='09:00')),
        migrations.AddField(model_name='templatetask',name='due_local_time',
                            field=models.CharField(max_length=5,default='17:00')),
    ]
