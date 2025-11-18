from django.db import migrations, models


def set_initial_hp(apps, schema_editor):
    Player = apps.get_model('game', 'Player')
    Player.objects.all().update(nudge_meter=100)


def revert_initial_hp(apps, schema_editor):
    Player = apps.get_model('game', 'Player')
    Player.objects.all().update(nudge_meter=0)


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0004_add_actual_counts_and_nudge_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='player',
            name='nudge_meter',
            field=models.IntegerField(default=100),
        ),
        migrations.RunPython(set_initial_hp, revert_initial_hp),
    ]
