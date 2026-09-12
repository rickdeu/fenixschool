# Legislação de Referência — Sistema de Educação de Angola

Esta pasta reúne a legislação angolana relevante para o desenho e a conformidade do
FenixSchool. Os PDFs foram obtidos de fontes públicas oficiais/repositórios jurídicos
(LEX.AO — Diário da República, APD, MAPTSS) em 2026-09-12. **Sempre confirmar a versão
em vigor** junto do Diário da República Eletrónico de Angola antes de qualquer decisão
de conformidade legal crítica, pois a legislação angolana é frequentemente actualizada.

## Índice de documentos

| Ficheiro | Diploma | Estado | Relevância para o FenixSchool |
|---|---|---|---|
| `lei-17-16-bases-sistema-educacao.pdf` | Lei n.º 17/16, de 7 de Outubro — Lei de Bases do Sistema de Educação e Ensino | Em vigor (com alterações da Lei 32/20) | Define subsistemas, níveis e ciclos de ensino, língua de ensino (português), estrutura geral que o módulo `academic` deve modelar |
| `lei-32-20-altera-lei-bases.pdf` | Lei n.º 32/20, de 12 de Agosto — Altera a Lei n.º 17/16 | Em vigor | Actualizações à Lei de Bases; ler em conjunto com a 17/16 |
| `decreto-presidencial-162-23-regime-ensino-primario-secundario.pdf` | Decreto Presidencial n.º 162/23, de 1 de Agosto — Regime Jurídico do Ensino Primário e Secundário do Subsistema de Ensino Geral | Em vigor (revoga o Decreto n.º 276/19) | Estrutura de direcção escolar (Director + Subdirectores Pedagógico e Administrativo), tipologia de instituições, idades de acesso (6 anos Primário, 12 anos I Ciclo, 15 anos II Ciclo), regras de assiduidade (3x carga semanal = máximo de faltas injustificadas), dimensão de turmas (máx. 36, até 45 nalgumas regiões; 26 em turmas inclusivas) — **directamente aplicável às regras de negócio de** `academic.Turma`, `enrollment.Matricula` **e** `attendance` |
| `lei-22-11-protecao-dados-pessoais.pdf` | Lei n.º 22/11, de 17 de Junho — Lei de Protecção de Dados Pessoais | Em vigor | Base legal para todo o tratamento de dados pessoais de alunos, encarregados e funcionários — ver [09-seguranca-e-privacidade.md](../09-seguranca-e-privacidade.md) |
| `lei-12-23-lei-geral-trabalho.pdf` | Lei n.º 12/23, de 27 de Dezembro — Lei Geral do Trabalho | Em vigor (revoga a Lei n.º 7/15) | Referência complementar para o módulo `hr` (contratos, vínculos, cessação) — o sistema **não substitui** um sistema de processamento salarial, mas os estados de contrato devem ser coerentes com esta lei |

## Documento não disponível em PDF (referência apenas por citação)

| Diploma | Estado | Nota |
|---|---|---|
| Decreto Executivo n.º 106/26 — Regulamento da Avaliação das Aprendizagens (RAA) dos Subsistemas da Educação Pré-Escolar, Ensino Geral e Educação de Adultos | Em vigor (revoga o Decreto Executivo n.º 424/25) | Não foi encontrado um PDF descarregável directamente; texto consultado via [angolex.com](https://angolex.com/paginas/decreto-executivo/regulamento-da-avaliacao-das-aprendizagens-dos-subsistemas-da-educacao-pre-escolar-ensino-geral-e-educacao-de-adultos-raa-106a-26a.html). Contém a **escala de avaliação oficial do Ensino Secundário** usada como base da parametrização de `grading` — ver resumo em [escala-avaliacao-secundario.md](escala-avaliacao-secundario.md) |

## Como esta legislação molda o sistema

- **Estrutura curricular** (`academic`): subsistemas, ciclos, níveis e idades de acesso
  vêm da Lei 17/16 (+ Lei 32/20) e do Decreto Presidencial 162/23.
- **Regras de assiduidade** (`attendance`): o limite de faltas injustificadas (3× a carga
  horária semanal) vem directamente do Decreto Presidencial 162/23 e deve ser o valor
  por omissão parametrizável em `core.Instituicao` (RF-FREQ-03).
- **Dimensão de turmas** (`academic.Turma`): os limites legais (36/45/26 alunos) devem
  ser os valores sugeridos por omissão em `numero_maximo_inscritos`, mas mantidos como
  parâmetro configurável (podem mudar por diploma futuro).
- **Escala de avaliação** (`grading`): a escala 0–20 com os níveis qualitativos
  (Excelente/Bom/Suficiente/Insuficiente/Mau) do Decreto Executivo 106/26 é a base da
  fórmula de cálculo por omissão (RF-INST-06) — ver
  [escala-avaliacao-secundario.md](escala-avaliacao-secundario.md).
- **Protecção de dados** (transversal): a Lei 22/11 fundamenta os requisitos de
  minimização, consentimento (encarregado de educação, para dados de menores) e direitos
  de acesso/rectificação detalhados em
  [09-seguranca-e-privacidade.md](../09-seguranca-e-privacidade.md).
- **Recursos Humanos** (`hr`): a Lei 12/23 fundamenta os tipos de vínculo contratual
  modelados em `hr.Contrato`.

## Nota de responsabilidade

Estes documentos são disponibilizados para **apoio ao desenho técnico e funcional** do
sistema. Não substituem aconselhamento jurídico. Antes do lançamento em produção,
recomenda-se validação por um jurista especializado em direito angolano da educação e em
protecção de dados, e confirmação da versão mais recente de cada diploma junto do Diário
da República Eletrónico (https://dre.gov.ao) ou do Ministério da Educação.
