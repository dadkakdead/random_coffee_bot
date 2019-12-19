# Generated by Django 2.2.2 on 2019-12-15 16:59

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('connector', '0007_auto_20191215_1810'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='meeting',
            name='message_user_a_id',
        ),
        migrations.RemoveField(
            model_name='meeting',
            name='message_user_b_id',
        ),
        migrations.RemoveField(
            model_name='meeting',
            name='sent_user_a_at',
        ),
        migrations.RemoveField(
            model_name='meeting',
            name='sent_user_b_at',
        ),
        migrations.AddField(
            model_name='meeting',
            name='updated_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]