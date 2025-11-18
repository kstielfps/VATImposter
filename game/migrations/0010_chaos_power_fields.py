# Generated manually for chaos power feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0009_merge_20241108_1926'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='palhaco_used_chaos_power',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='player',
            name='impostor_knows_clown',
            field=models.BooleanField(default=False),
        ),
    ]
