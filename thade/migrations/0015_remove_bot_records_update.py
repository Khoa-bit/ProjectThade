# Generated by Django 3.2.5 on 2021-07-27 02:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('thade', '0014_bot_records_update'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bot',
            name='records_update',
        ),
    ]
