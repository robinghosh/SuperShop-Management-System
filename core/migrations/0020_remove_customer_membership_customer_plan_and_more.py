# Generated by Django 5.1.6 on 2025-03-27 16:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_membership_customer_customername_customer_membership'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customer',
            name='memberShip',
        ),
        migrations.AddField(
            model_name='customer',
            name='plan',
            field=models.CharField(choices=[('R', 'Regular'), ('S', 'Silver'), ('G', 'Gold'), ('D', 'Diamond')], default='R', max_length=20),
        ),
        migrations.DeleteModel(
            name='MemberShip',
        ),
    ]
