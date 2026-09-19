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
from django.utils.translation import override as translation_override

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
    Django para ecrã e para PDF").

    Issue #152 (RF-I18N-03): um documento oficial nunca é traduzido, por
    validade legal/administrativa -- `translation_override("pt")` ignora o
    `preferred_language` do utilizador autenticado (activado por
    `LocaleMiddleware`/issue #149 em todo o resto do pedido) só durante esta
    renderização."""

    with translation_override("pt"):
        html = render_to_string(template_name, context)
    return weasyprint.HTML(string=html).write_pdf()


PAUTA_OFICIAL_DOCUMENT_TYPE = "pauta-oficial"


def gerar_pauta_oficial_pdf(
    *,
    school_class,
    subject,
    evaluation_type,
    academic_term,
    grades,
    issued_by,
    origin_node_id,
) -> tuple[IssuedDocument, bytes]:
    """RF-REL-03 (issue #96): "reaproveita a view de Pauta de `grading`,
    exportando em PDF via WeasyPrint" -- o chamador (`grading`'s
    `pauta_oficial_pdf_view`) já resolveu a mesma selecção turma/disciplina/
    tipo/trimestre e as mesmas `grades` que `pauta_detail_view` mostra no
    ecrã; esta função só regista a emissão (numeração/auditoria) e
    renderiza o PDF -- `reports` não importa nenhum modelo de `grading`
    para o fazer."""

    issued = emitir_documento(
        institution=school_class.institution,
        document_type=PAUTA_OFICIAL_DOCUMENT_TYPE,
        issued_by=issued_by,
        origin_node_id=origin_node_id,
    )
    pdf = render_document_pdf(
        "reports/pauta_oficial.html",
        {
            "institution": school_class.institution,
            "issued_document": issued,
            "school_class": school_class,
            "subject": subject,
            "evaluation_type": evaluation_type,
            "academic_term": academic_term,
            "grades": grades,
        },
    )
    return issued, pdf


def gerar_declaracao_pdf(
    *, institution, declaracao_type: str, title: str, legal_text: str, issued_by, origin_node_id
) -> tuple[IssuedDocument, bytes]:
    """RF-REL-01 (issue #94): "3 tipos de declaração geráveis em PDF" --
    genérico para os 3 (matrícula/frequência/conclusão): o chamador
    (`apps.enrollment.services.emitir_declaracao`) já validou o tipo contra
    o estado da matrícula e resolveu `title`/`legal_text`; esta função só
    regista a emissão e renderiza o PDF."""

    issued = emitir_documento(
        institution=institution,
        document_type=declaracao_type,
        issued_by=issued_by,
        origin_node_id=origin_node_id,
    )
    pdf = render_document_pdf(
        "reports/declaracao.html",
        {
            "institution": institution,
            "issued_document": issued,
            "title": title,
            "legal_text": legal_text,
        },
    )
    return issued, pdf


COMPROVATIVO_MATRICULA_DOCUMENT_TYPE = "comprovativo-matricula"


def gerar_comprovativo_matricula_pdf(
    *, institution, fields: dict, issued_by, origin_node_id
) -> tuple[IssuedDocument, bytes]:
    """RF-MAT-06 (issue #48): "comprovativo imprimível imediatamente após
    confirmação da matrícula" -- o chamador
    (`apps.enrollment.services.emitir_comprovativo_matricula`) já resolveu
    todos os campos a mostrar (`fields`, um dict simples de etiqueta →
    valor); esta função só regista a emissão e renderiza o PDF."""

    issued = emitir_documento(
        institution=institution,
        document_type=COMPROVATIVO_MATRICULA_DOCUMENT_TYPE,
        issued_by=issued_by,
        origin_node_id=origin_node_id,
    )
    pdf = render_document_pdf(
        "reports/comprovativo_matricula.html",
        {
            "institution": institution,
            "issued_document": issued,
            "fields": fields,
        },
    )
    return issued, pdf


BOLETIM_DOCUMENT_TYPE = "boletim"


def gerar_boletim_pdf(
    *, enrollment, academic_term, rows, issued_by, origin_node_id
) -> tuple[IssuedDocument, bytes]:
    """RF-REL-04 (issue #97): "reaproveita a view de Boletim de `grading`,
    exportando em PDF" -- o chamador (`grading`'s `boletim_pdf_view`) já
    resolveu o mesmo aluno/trimestre e as mesmas `rows`
    (`apps.grading.services.get_boletim_rows`) que `boletim_view` mostra no
    ecrã; esta função só regista a emissão e renderiza o PDF."""

    issued = emitir_documento(
        institution=enrollment.institution,
        document_type=BOLETIM_DOCUMENT_TYPE,
        issued_by=issued_by,
        origin_node_id=origin_node_id,
    )
    pdf = render_document_pdf(
        "reports/boletim.html",
        {
            "institution": enrollment.institution,
            "issued_document": issued,
            "enrollment": enrollment,
            "academic_term": academic_term,
            "rows": rows,
        },
    )
    return issued, pdf
