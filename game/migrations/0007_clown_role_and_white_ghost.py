from django.db import migrations, models


def bump_max_players(apps, schema_editor):
    Game = apps.get_model('game', 'Game')
    Game.objects.all().update(max_players=12)


def revert_max_players(apps, schema_editor):
    Game = apps.get_model('game', 'Game')
    Game.objects.filter(max_players=12).update(max_players=8)


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0006_alter_player_nudge_meter'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='num_clowns',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='game',
            name='actual_num_clowns',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='game',
            name='winning_team',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='game',
            name='max_players',
            field=models.IntegerField(default=12),
        ),
        migrations.RunPython(bump_max_players, revert_max_players),
        migrations.AddField(
            model_name='player',
            name='palhaco_known_impostors',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='player',
            name='palhaco_goal_state',
            field=models.CharField(choices=[('', 'Sem Objetivo'), ('finding', 'Encontrando Impostor'), ('pending', 'Aguardando Atualização'), ('eliminate', 'Precisa ser Eliminado')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='player',
            name='palhaco_goal_ready_round',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='player',
            name='role',
            field=models.CharField(blank=True, choices=[('citizen', 'Cidadão'), ('impostor', 'Impostor'), ('whiteman', 'WhiteMan'), ('clown', 'Palhaço')], max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='vote',
            name='is_palhaco_guess',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterUniqueTogether(
            name='vote',
            unique_together={('game', 'voter', 'round_number', 'is_palhaco_guess')},
        ),
    ]
