# Generated by Django 5.1.5 on 2025-01-23 21:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_inventory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventory',
            name='barcode',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
