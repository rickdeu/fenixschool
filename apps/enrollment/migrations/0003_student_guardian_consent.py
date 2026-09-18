# Generated manually (issue #143, RNF-AUD-02) -- see the model docstring in
# apps/enrollment/models/student_model.py. Written by hand rather than via
# `makemigrations` (which insists on an interactive one-off default for a new
# NOT NULL column) as a two-step add-nullable-then-tighten instead: no
# `Student` row exists yet in any environment this project has been deployed
# to, so tightening to NOT NULL immediately afterwards never conflicts with
# any existing data.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("enrollment", "0002_candidate_enrollment"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="guardian_consent_given_at",
            field=models.DateTimeField(
                auto_now_add=True,
                null=True,
                help_text="Registado automaticamente no momento da Inscrição.",
                verbose_name="consentimento dado em",
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="guardian_consent_given_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="consented_students",
                to="enrollment.guardian",
                help_text=(
                    "Encarregado de Educação que deu o consentimento no acto de Inscrição."
                ),
                verbose_name="consentimento dado por",
            ),
        ),
        migrations.AlterField(
            model_name="student",
            name="guardian_consent_given_at",
            field=models.DateTimeField(
                auto_now_add=True,
                help_text="Registado automaticamente no momento da Inscrição.",
                verbose_name="consentimento dado em",
            ),
        ),
        migrations.AlterField(
            model_name="student",
            name="guardian_consent_given_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="consented_students",
                to="enrollment.guardian",
                help_text=(
                    "Encarregado de Educação que deu o consentimento no acto de Inscrição."
                ),
                verbose_name="consentimento dado por",
            ),
        ),
    ]
