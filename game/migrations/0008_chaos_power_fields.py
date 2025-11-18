# Generated manually for chaos power feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0007_clown_role_and_white_ghost'),
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
