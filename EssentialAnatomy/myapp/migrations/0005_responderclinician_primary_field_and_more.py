# Generated by Django 4.2.15 on 2024-08-26 18:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_remove_processedresponseanatomy_average_rating_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='responderclinician',
            name='primary_field',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='responderclinician',
            name='subfield',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
