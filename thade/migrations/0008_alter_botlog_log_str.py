# Generated by Django 3.2.5 on 2021-07-22 11:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thade', '0007_botlog_log_str'),
    ]

    operations = [
        migrations.AlterField(
            model_name='botlog',
            name='log_str',
            field=models.CharField(max_length=128),
        ),
    ]
