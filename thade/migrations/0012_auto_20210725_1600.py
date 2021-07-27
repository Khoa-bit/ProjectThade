# Generated by Django 3.2.5 on 2021-07-25 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thade', '0011_rename_state_bot_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='botlog',
            name='investment_vnd',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='botlog',
            name='signal',
            field=models.CharField(choices=[('BUY', 'Buy'), ('SELL', 'Sell'), ('HOLD', 'Hold'), ('NOT_BUY', 'Cannot afford to Buy'), ('NOT_SELL', 'Not enough stocks to Sell'), ('INVEST', 'Invest'), ('WITHDRAW', 'Withdraw'), ('ERR', 'Invalid signal')], default='ERR', max_length=16),
        ),
    ]