# Generated by Django 4.2.7 on 2024-02-29 03:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0002_dailyrecord_empcode_temporay_empcode'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='temporay',
            name='employee_number',
        ),
    ]
