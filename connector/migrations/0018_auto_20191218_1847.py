# Generated by Django 2.2.2 on 2019-12-18 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('connector', '0017_remove_message_callback_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='gender',
            field=models.CharField(blank=True, choices=[('M', 'Мужчина'), ('F', 'Женщина')], max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='meeting_frequency',
            field=models.CharField(blank=True, choices=[('H', 'Два и более раз в неделю 🐆'), ('M', 'Раз в неделю 🐇'), ('L', 'Раз в две недели 🐢')], max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='meeting_motivation',
            field=models.CharField(blank=True, choices=[('D', 'Найти вторую половину ❤'), ('N', 'Поговорить о работе'), ('HF', 'Просто отдохнуть')], max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='type',
            field=models.CharField(blank=True, choices=[('I', 'Один'), ('T', 'С коллегами')], max_length=100, null=True),
        ),
    ]
