# Generated by Django 3.2.5 on 2021-07-13 09:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('thade', '0003_auto_20210712_0925'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='record',
            name='percentage_diff',
        ),
        migrations.RemoveField(
            model_name='record',
            name='value_diff_vnd',
        ),
    ]
