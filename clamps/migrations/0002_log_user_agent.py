# Generated by Django 5.2.3 on 2025-06-14 06:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clamps', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='log',
            name='user_agent',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='用户代理'),
        ),
    ]
