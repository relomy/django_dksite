# Generated by Django 2.2.5 on 2019-09-04 13:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DKResultOwnership',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dk_id', models.CharField(max_length=15, unique=True)),
                ('ownership', models.FloatField()),
                ('fpts', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ('contest', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ownership', to='results.DKContest')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='player_ownership', to='results.Player')),
            ],
            options={
                'unique_together': {('contest', 'player')},
            },
        ),
    ]