# Generated by Django 2.2.5 on 2019-09-06 00:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0005_auto_20190905_2050'),
    ]

    operations = [
        migrations.AddField(
            model_name='dkcontest',
            name='draft_group_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
