# Generated by Django 5.1.6 on 2025-02-27 12:16

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Referral",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("bonus_received", models.BooleanField(default=False)),
                (
                    "referred_user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referred_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "referrer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referrals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
