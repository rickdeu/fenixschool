# Written by hand rather than via `makemigrations` (which insists on an
# interactive one-off default for a new NOT NULL column), as a two-step
# add-nullable-then-tighten instead -- same reasoning as
# 0003_student_guardian_consent: no `Candidate` row has ever gone through
# this new document_type/document_number/document_expiry_date trio (issue
# #102's public pre-application form, apps/enrollment/models/candidate_model.py),
# so tightening to NOT NULL immediately afterwards never conflicts with any
# existing data.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_institution_description"),
        ("enrollment", "0003_student_guardian_consent"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidate",
            name="document_type",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="candidates",
                to="core.identificationdocumenttype",
                verbose_name="tipo de documento",
            ),
        ),
        migrations.AddField(
            model_name="candidate",
            name="document_number",
            field=models.CharField(
                default="", max_length=50, blank=True, verbose_name="número do documento"
            ),
        ),
        migrations.AddField(
            model_name="candidate",
            name="document_expiry_date",
            field=models.DateField(null=True, verbose_name="data de validade do documento"),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="document_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="candidates",
                to="core.identificationdocumenttype",
                verbose_name="tipo de documento",
            ),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="document_number",
            field=models.CharField(max_length=50, verbose_name="número do documento"),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="document_expiry_date",
            field=models.DateField(verbose_name="data de validade do documento"),
        ),
    ]
