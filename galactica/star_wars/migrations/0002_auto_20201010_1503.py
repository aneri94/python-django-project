# Generated by Django 3.0.8 on 2020-10-10 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('star_wars', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='people',
            options={'verbose_name_plural': 'People'},
        ),
        migrations.AlterModelOptions(
            name='species',
            options={'verbose_name_plural': 'Species'},
        ),
        migrations.AlterField(
            model_name='people',
            name='created',
            field=models.DateTimeField(auto_created=True, auto_now_add=True),
        ),
    ]