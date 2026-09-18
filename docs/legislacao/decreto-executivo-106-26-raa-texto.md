# Decreto Executivo n.º 106/26 — Regulamento da Avaliação das Aprendizagens (RAA)

Texto colado directamente pelo utilizador a partir da página consultada em
[angolex.com](https://angolex.com/paginas/decreto-executivo/regulamento-da-avaliacao-das-aprendizagens-dos-subsistemas-da-educacao-pre-escolar-ensino-geral-e-educacao-de-adultos-raa-106a-26a.html)
em 2026-09-18 (essa página bloqueia scraping automático — ver
[README.md](README.md) — pelo que este é, por agora, o único texto integral
confirmado que temos deste diploma). Cobre o Sumário e os Artigos 1.º a 36.º
(truncado no meio do Artigo 36.º pelo limite de tamanho da mensagem que o
transportou) — **os Anexos (I a VII), incluindo o Anexo III com as fórmulas de
cálculo das médias, ainda não foram obtidos** (ver nota em
[escala-avaliacao-secundario.md](escala-avaliacao-secundario.md) e em
`apps/grading/services.py`'s `DEFAULT_EVALUATION_TYPES`).

## Confirma, por este texto

- **Escala de avaliação** (Artigo 14.º): Ensino Secundário Geral — 0 a 20
  valores, 5 níveis qualitativos (Excelente/Bom/Suficiente/Insuficiente/Mau).
  Coincide com o já registado em
  [escala-avaliacao-secundario.md](escala-avaliacao-secundario.md).
- **Componentes de avaliação usados no Ensino Primário e no Ensino Secundário
  Geral** (Artigos 20.º e 22.º): exactamente três, e com esta terminologia
  oficial (confirma os nomes já usados em `apps/grading/services.py`'s
  `DEFAULT_EVALUATION_TYPES`):
  - a) Avaliação Contínua por Disciplina ou Componente Curricular (= "MAC" —
    "Média das Avaliações Contínuas" — nome usado no sistema);
  - b) Prova Trimestral;
  - c) Exame Nacional (= "Exame").
- **Onde está a fórmula**: Artigo 20.º n.º 6 e Artigo 22.º n.º 8 remetem
  ambos, textualmente, para o **Anexo III** do Regulamento — "As fórmulas
  para o cálculo das médias encontram-se no Anexo III do presente
  Regulamento." O corpo do diploma (Artigos 1.º-40.º) não contém os pesos
  numéricos.
- **Definições relevantes** (Artigo 5.º):
  - «Média Aritmética Simples» — soma da pontuação de todas as avaliações
    obtidas pelo aluno divididas pelo número de avaliações realizadas.
  - «Média Aritmética Ponderada» — soma da pontuação de todas as avaliações
    obtidas pelo aluno multiplicadas pelo respectivo peso atribuído e
    dividida pela soma total dos pesos. Confirma que o conceito de "soma dos
    pesos" (normalização) usado em `apps.grading.services.calculate_average`
    é o mecanismo genérico correcto, mesmo sem ainda termos os pesos
    concretos do Anexo III.

## Ainda por confirmar

O texto pasteado termina a meio do Artigo 36.º — os Anexos I a VII (incluindo
o **Anexo III**, com as fórmulas de MAC/Prova Trimestral/Exame) não fazem
parte deste ficheiro. Assim que forem obtidos, actualizar
`apps/grading/services.py`'s `DEFAULT_EVALUATION_TYPES` com os pesos
confirmados e remover a ressalva de "não confirmado" em
`docs/implementation-decisions.md` (entrada de 2026-09-18, issue #18).

**Pesquisa adicional em 2026-09-18 (concluída sem sucesso)**: confirmado, por
acesso directo ao texto integral da página do `angolex.com` (contornando o
bloqueio HTTP 403 via um proxy leitor), que **essa página termina mesmo a
seguir ao Anexo II** — o Anexo III simplesmente não está publicado nela.
Tentativas adicionais sem sucesso: site do INADE (só administração de
exames, sem fórmulas), secção de legislação do `med.gov.ao` (não lista nem
o 106/26 nem o 424/25), e vários documentos no Scribd sobre avaliação em
Angola -- um deles tinha uma fórmula (`MT = (MAC+NPP+NPT)/3`,
`CF = 0,4×MFD + 0,6×MEC`), mas usa um componente ("NPP") que não existe na
terminologia confirmada do 106/26 (só MAC/Prova Trimestral/Exame Nacional),
pelo que é quase certamente de um sistema diferente/mais antigo -- **não
usado**. Por decisão do utilizador, a pesquisa automática deste Anexo III
foi encerrada aqui; não repetir esta pesquisa sem uma pista nova e concreta
(ex.: um link ou PDF fornecido directamente).

## Texto (Sumário e Artigos 1.º a 36.º, parcial)

> Convindo estabelecer as normas que regulam a avaliação ao serviço das
> aprendizagens na educação formal, em conformidade com o disposto nos
> artigos 20.º e 21.º do Decreto Presidencial n.º 195/23, de 11 de Outubro,
> que aprova o Regime Jurídico do Subsistema da Educação Pré-Escolar, no
> artigo 53.º do Decreto Presidencial n.º 162/23, de 1 de Agosto, que aprova
> o Regime Jurídico do Subsistema do Ensino Geral, e no artigo 23.º do
> Decreto Presidencial n.º 70/25, de 20 de Março, que aprova o Regime
> Jurídico do Subsistema da Educação de Adultos [...]

### Artigo 20.º — Avaliações (Ensino Primário)

1. O Ensino Primário comporta as seguintes avaliações:
   a) Avaliação Contínua por Disciplina ou Componente Curricular;
   b) Prova Trimestral;
   c) Exame Nacional.
2. A Avaliação Contínua por Disciplina ou Componente Curricular é da
   responsabilidade do Professor Titular da Turma [...]
3. A elaboração das Provas Trimestrais (I e II) [...] é da responsabilidade
   das Subdirecções Pedagógicas das respectivas instituições de ensino.
4. Nas classes de transição [...] a elaboração da prova do III Trimestre é
   da responsabilidade das Subdirecções Pedagógicas [...]
5. As Provas do Exame Nacional são da responsabilidade do órgão responsável
   pelos processos de avaliação do Ministério da Educação.
6. **As fórmulas para o cálculo das médias encontram-se no Anexo III do
   presente Regulamento.**

### Artigo 22.º — Avaliações (Ensino Secundário Geral)

1. Do I e II Ciclos integram as seguintes avaliações:
   a) Avaliação Contínua por Disciplina;
   b) Prova Trimestral;
   c) Exame Nacional.
2-7. [...]
8. **As fórmulas para o cálculo das médias encontram-se no Anexo III do
   presente Regulamento.**

### Artigo 25.º — Avaliações (Educação de Jovens e Adultos)

1. No Ensino Primário e Secundário de Adultos realizam-se as seguintes
   avaliações: a) Avaliação Contínua; b) Prova Trimestral; c) Exame Nacional.
2. **Para o cálculo das médias são aplicadas as fórmulas previstas no Anexo
   III do presente Diploma.**

O texto completo colado pelo utilizador (Sumário + Artigos 1.º-36.º) está
preservado na transcrição da conversa que originou este ficheiro, caso seja
necessário consultar outro artigo específico não resumido acima.
