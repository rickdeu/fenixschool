# Escala de Avaliação do Ensino Secundário (Angola)

Fonte: Decreto Executivo n.º 106/26 — Regulamento da Avaliação das Aprendizagens (RAA)
dos Subsistemas da Educação Pré-Escolar, Ensino Geral e Educação de Adultos (revoga o
Decreto Executivo n.º 424/25). Texto consultado em
[angolex.com](https://angolex.com/paginas/decreto-executivo/regulamento-da-avaliacao-das-aprendizagens-dos-subsistemas-da-educacao-pre-escolar-ensino-geral-e-educacao-de-adultos-raa-106a-26a.html)
em 2026-09-12; não foi localizado PDF oficial descarregável directamente — **confirmar
texto integral junto do Diário da República ou do MED antes de uso normativo**.

## Escala oficial — Ensino Secundário Geral e de Jovens e Adultos (Anexo II)

| Nível | Classificação quantitativa | Percentagem | Nível qualitativo |
|---|---|---|---|
| 1.º | 17–20 | 85–100% | Excelente |
| 2.º | 14–16 | 70–84% | Bom |
| 3.º | 10–13 | 50–69% | Suficiente |
| 4.º | 6–9 | 30–49% | Insuficiente |
| 5.º | 0–5 | 0–29% | Mau |

Nota mínima de aprovação: **10 valores** (fronteira entre "Insuficiente" e "Suficiente").

## Aplicação no modelo de dados

Esta tabela corresponde a `grading.EscalaAvaliacao`, referenciada por
`core.Instituicao.formula_media_default` (ver
[05-modelo-de-dados.md](../05-modelo-de-dados.md)) para:

- Validar que toda `Nota.classificacao` está no intervalo 0–20 (RF-AVAL-03).
- Apresentar, além do valor numérico, o **nível qualitativo** em pautas e boletins
  (RF-AVAL-05), tal como exigido pelo regulamento oficial.
- Determinar a situação final do aluno (aprovado a partir de 10 valores/3.º nível,
  RF-AVAL-07), sujeito à fórmula de cálculo de média parametrizada por
  disciplina/curso/ano lectivo (que pode combinar MAC, Prova Trimestral e Exame,
  conforme regulamentação específica de cada modalidade de ensino).

## Recomendação de implementação

Carregar esta escala como **fixture de sistema** (`core/fixtures/escala_avaliacao.json`),
editável apenas por um Super Administrador, dado tratar-se de um parâmetro normativo
nacional e não uma preferência de cada instituição.
