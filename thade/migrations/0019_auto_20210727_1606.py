# Generated by Django 3.2.5 on 2021-07-27 16:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thade', '0018_alter_botlog_signal'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bot',
            name='investment_vnd',
        ),
        migrations.RemoveField(
            model_name='botlog',
            name='investment_vnd',
        ),
        migrations.AddField(
            model_name='botlog',
            name='decimal_investment_vnd',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=16),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='bot',
            name='fee',
            field=models.DecimalField(decimal_places=6, max_digits=12),
        ),
    ]