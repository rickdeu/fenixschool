"""Exportações normativas em formatos abertos (issue #117, RF-ADM-05):
backup manual/exportação por entidade, em CSV, JSON e PDF.

`Financeiro` fica de fora por agora -- o módulo `finance` ainda não tem
modelos (M3), tal como já documentado em `apps/audit/signals.py` para o
mesmo motivo.
"""

import csv
import io
import json

import weasyprint
from django.core import serializers
from django.http import HttpResponse
from django.template.loader import render_to_string


def _students_queryset(institution):
    from apps.enrollment.models import Student

    return Student.objects.filter(institution=institution).order_by("first_name", "last_name")


def _enrollments_queryset(institution):
    from apps.enrollment.models import Enrollment

    return (
        Enrollment.objects.filter(institution=institution)
        .select_related("student", "school_class")
        .order_by("-academic_year", "student__first_name")
    )


def _grades_queryset(institution):
    from apps.grading.models import Grade

    return (
        Grade.objects.filter(institution=institution)
        .select_related("student", "subject", "evaluation_type", "academic_term")
        .order_by("-academic_term", "student__first_name")
    )


# Cada entidade: a queryset (com FKs pré-resolvidas para a exportação em
# CSV/PDF) e as colunas (rótulo, um "getter" que lê um valor legível do
# objecto) mostradas nesses dois formatos -- a exportação em JSON usa antes
# `serializers.serialize`, genérico, com todos os campos concretos do
# modelo (o mesmo mecanismo já usado por `apps.sync.signals`/issue #144's
# `apps.admin_panel.services`).
EXPORTABLE_ENTITIES = {
    "alunos": {
        "label": "Alunos",
        "queryset_fn": _students_queryset,
        "columns": [
            ("Nº de aluno", lambda s: s.student_number),
            ("Nome", str),
            ("Data de nascimento", lambda s: s.birth_date),
            ("Género", lambda s: s.get_gender_display()),
            ("Nº de documento", lambda s: s.document_number),
            ("Estado", lambda s: s.get_status_display()),
        ],
    },
    "matriculas": {
        "label": "Matrículas",
        "queryset_fn": _enrollments_queryset,
        "columns": [
            ("Nº de matrícula", lambda e: e.enrollment_number),
            ("Aluno", lambda e: str(e.student)),
            ("Turma", lambda e: e.school_class.designation),
            ("Ano lectivo", lambda e: str(e.academic_year)),
            ("Estado", lambda e: e.get_status_display()),
        ],
    },
    "notas": {
        "label": "Notas",
        "queryset_fn": _grades_queryset,
        "columns": [
            ("Aluno", lambda g: str(g.student)),
            ("Disciplina", lambda g: g.subject.name),
            ("Tipo de avaliação", lambda g: g.evaluation_type.name),
            ("Trimestre", lambda g: str(g.academic_term)),
            ("Classificação", lambda g: g.value),
        ],
    },
}


def _csv_response(entity_key: str, institution) -> HttpResponse:
    entity = EXPORTABLE_ENTITIES[entity_key]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([label for label, _ in entity["columns"]])
    for obj in entity["queryset_fn"](institution):
        writer.writerow([getter(obj) for _, getter in entity["columns"]])

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{entity_key}.csv"'
    return response


def _json_response(entity_key: str, institution) -> HttpResponse:
    entity = EXPORTABLE_ENTITIES[entity_key]
    rows = json.loads(serializers.serialize("json", entity["queryset_fn"](institution)))
    payload = [{"id": row["pk"], **row["fields"]} for row in rows]

    response = HttpResponse(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{entity_key}.json"'
    return response


def _pdf_response(entity_key: str, institution) -> HttpResponse:
    entity = EXPORTABLE_ENTITIES[entity_key]
    rows = [
        [getter(obj) for _, getter in entity["columns"]]
        for obj in entity["queryset_fn"](institution)
    ]
    html = render_to_string(
        "admin_panel/data_export_pdf.html",
        {
            "institution": institution,
            "title": entity["label"],
            "headers": [label for label, _ in entity["columns"]],
            "rows": rows,
        },
    )
    pdf = weasyprint.HTML(string=html).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{entity_key}.pdf"'
    return response


EXPORT_RENDERERS = {
    "csv": _csv_response,
    "json": _json_response,
    "pdf": _pdf_response,
}


def export_entity(entity_key: str, formato: str, institution) -> HttpResponse:
    return EXPORT_RENDERERS[formato](entity_key, institution)
