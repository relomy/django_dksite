# Generated by Django 2.2.5 on 2019-09-06 00:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0004_auto_20190904_0958'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dkcontestpayout',
            name='lower_rank',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='dkcontestpayout',
            name='upper_rank',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='dkresult',
            name='rank',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
