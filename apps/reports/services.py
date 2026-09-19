"""Regras de negócio e transações da app `reports`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.

RF-REL-06 (issue #93): base reutilizável para todo documento oficial --
numeração/série nunca reutilizada (mesmo que a geração do PDF em si falhe
depois de reservado o número) e registo automático em auditoria (via
`apps.audit.signals.audit_model`, ligado a `IssuedDocument` em
`ReportsConfig.ready()`). As issues #94/#96/#97 chamam `emitir_documento()`
e `render_document_pdf()` a partir dos seus próprios tipos de documento
concretos -- esta app não fabrica esses tipos antes de existirem.
"""

import weasyprint
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from .models import DocumentSequence, IssuedDocument


def _reserve_document_number(
    *, institution, document_type: str, origin_node_id
) -> tuple[int, str]:
    """Reserva, numa transacção própria já submetida antes de devolver, o
    próximo número da sequência de `document_type` para `institution` --
    para que uma falha posterior (ex. na geração do PDF) nunca liberte nem
    reutilize este número."""

    with transaction.atomic():
        sequence = (
            DocumentSequence.all_objects.select_for_update()
            .filter(institution=institution, document_type=document_type)
            .first()
        )
        if sequence is None:
            # Uma corrida rara entre dois pedidos concorrentes para o
            # mesmíssimo tipo de documento, ainda sem sequência criada,
            # levantaria `IntegrityError` na restrição única
            # (institution, document_type) -- não tratado aqui, tal como
            # nenhuma outra sequência/contador deste projecto trata essa
            # janela (arquitectura assume um único Nó Local por instituição).
            sequence = DocumentSequence.all_objects.create(
                institution=institution,
                origin_node_id=origin_node_id,
                document_type=document_type,
                last_number=0,
            )
        sequence.last_number += 1
        sequence.save(update_fields=["last_number", "updated_at", "version"])
        number = sequence.last_number

    year = timezone.now().year
    formatted_number = f"{document_type.upper()}/{year}/{number:06d}"
    return number, formatted_number


def emitir_documento(
    *, institution, document_type: str, issued_by, origin_node_id
) -> IssuedDocument:
    """RF-REL-06: regista a emissão de um novo documento oficial, com
    numeração/série reservada por `_reserve_document_number` e entrada de
    auditoria automática (`IssuedDocument` está ligado a `audit_model` --
    ver `ReportsConfig.ready()`)."""

    number, formatted_number = _reserve_document_number(
        institution=institution, document_type=document_type, origin_node_id=origin_node_id
    )
    return IssuedDocument.objects.create(
        institution=institution,
        origin_node_id=origin_node_id,
        document_type=document_type,
        number=number,
        formatted_number=formatted_number,
        issued_by=issued_by,
    )


def render_document_pdf(template_name: str, context: dict) -> bytes:
    """Renderiza `template_name` (que deve extender
    `reports/base_document.html`) para PDF via WeasyPrint -- reaproveita o
    mesmo motor de templates Django usado para ecrã (docs/10-stack-
    tecnologica-e-estrutura-projeto.md §10.1: "Reutiliza os mesmos templates
    Django para ecrã e para PDF")."""

    html = render_to_string(template_name, context)
    return weasyprint.HTML(string=html).write_pdf()
