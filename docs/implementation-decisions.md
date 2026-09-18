# Implementation Decisions

Registo de decisões técnicas tomadas quando uma task, a documentação e o código
existente não determinavam sozinhos o comportamento a implementar (ver `CLAUDE.md`).
O estado/progresso de cada task em si é acompanhado nas issues do GitHub, não aqui —
este ficheiro é só para decisões que precisam de justificação e contexto duradouros.

## 2026-09-17 — Issue #142 (TLS 1.2+): âmbito faseado

**Contexto**: Issue #142 pede TLS 1.2+ em todos os endpoints, mais autenticação mútua
Nó↔Nó além do TLS.

**Problema**: os endpoints de sincronização (`apps.api`, push/pull entre Nó Local e Nó
Central — docs/08-offline-first-e-sincronizacao.md §8.5) ainda não existem (são scope de
M5). Implementar "autenticação mútua Nó-Nó" sem endpoints reais para proteger seria
código fictício sem uso real, o que as instruções do projecto proíbem explicitamente.

**Opções**:
1. Bloquear toda a issue até M5 (nenhum progresso agora).
2. Implementar apenas a parte de infraestrutura TLS genérica (Nginx, certificados) agora,
   e a autenticação mútua Nó-Nó junto da implementação real dos endpoints de sync (M5).
3. Fabricar uma verificação de mTLS "de fachada" já agora, sem endpoint real a proteger.

**Decisão**: Opção 2.

**Justificação**: A parte de TLS 1.2+/Nginx/certificados é infra-estrutural, testável e
útil desde já (protege inclusivamente o `/admin/` e qualquer ecrã futuro), e não depende
de nenhuma outra issue. A autenticação mútua Nó-Nó só faz sentido semântico quando existe
um pedido de sincronização real a autenticar — implementá-la antes disso violaria a regra
do projecto contra funcionalidades fictícias/mockadas.

**Impacto**: issue #142 permanece aberta (não marcada como `DONE`) com um comentário a
explicar a parte entregue e a parte em falta; será fechada quando a autenticação mútua
Nó-Nó for implementada junto dos endpoints `apps.api` de sincronização (M5).

## 2026-09-18 — Issue #34 (`academic.SchoolClass`): `academic_term` opcional

**Contexto**: docs/05-modelo-de-dados.md §5.8 lista `periodo_lectivo_id` (FK
`PeriodoLectivo`) como campo de `Turma`, sem a marca "novo" que os restantes campos
acrescentados nesta reformulação carregam.

**Problema**: uma Turma agrupa alunos tipicamente durante todo o Ano Lectivo, não apenas
um Período Lectivo (trimestre/semestre) — obrigar `academic_term` a um valor fixo exigiria
criar uma Turma por período (3 linhas por ano lectivo num sistema trimestral), o que
contradiz a forma como turmas são geridas na prática (a mesma turma atravessa os vários
períodos).

**Opções**:
1. Seguir a tabela à letra: `academic_term` obrigatório.
2. Tornar `academic_term` opcional (`null=True, blank=True`), preservando o campo para
   os casos em que uma turma esteja de facto ligada a um único período.

**Decisão**: Opção 2.

**Justificação**: Tornar o campo obrigatório introduziria um comportamento
operacionalmente estranho sem que nenhum requisito funcional (RF-CURR-05) o exija
explicitamente — RF-CURR-05 nem sequer menciona período lectivo na descrição da Turma,
apenas o exemplo de implementação o lista. Mantê-lo opcional preserva o campo (não é
fabricação nem omissão silenciosa) sem forçar um modelo de dados pouco natural.

**Impacto**: `academic.SchoolClass.academic_term` é `null=True, blank=True`. Se uma
necessidade real de Turma-por-período surgir mais tarde (ex.: disciplinas semestrais
lecionadas por uma sub-turma), revisitar esta decisão nessa altura.

## 2026-09-18 — Issue #18 (fórmula de média): pesos por omissão sem fonte MED confirmada

**Contexto**: RF-INST-06 pede que a fórmula de cálculo de média (pesos de MAC/Prova
Trimestral/Exame) seja semeada com um valor por omissão logo na criação da instituição
(não apenas sugerida lazily na primeira visita ao ecrã de configuração), idealmente
reflectindo o que o Ministério da Educação (MED) exige.

**Problema**: o regulamento angolano em vigor é o Decreto Executivo n.º 106/26 (RAA —
ver docs/legislacao/escala-avaliacao-secundario.md, já registado numa issue anterior
como sem PDF oficial descarregável directamente). Tentámos confirmar os pesos exactos
por pesquisa na Internet:

1. Uma fórmula inicialmente promissora (`MT = (2×MAC+PT)/3`) revelou-se, ao ler o texto
   extraído do PDF, ser do **Diploma Ministerial n.º 59/2015 de Moçambique**, não de
   Angola — descartada.
2. O decreto revogado anterior (424/25) tem um PDF oficial real em `lex.ao`, mas é
   digitalizado como imagem (sem texto extraível por `pypdf`); um resumo por IA de uma
   página sobre esse decreto sugeriu `MT = (MACT+NPT)/2` (50%/50%), mas sem conseguir
   verificar directamente no texto e sendo já revogado, não foi usado.
3. A página do 106/26 (`angolex.com`) bloqueia scraping automático (HTTP 403); não foi
   encontrado nenhum PDF de texto extraível para o regulamento em vigor.

**Opções**:
1. Bloquear a semeação de um valor por omissão até se confirmar o texto oficial do
   106/26.
2. Semear um valor genérico e claramente identificado como sugestão editável, não como
   exigência confirmada do MED.

**Decisão**: Opção 2 (confirmada com o utilizador via pergunta directa).

**Justificação**: um formulário de fórmula vazio bloquearia todo o cálculo de médias
até um Administrador o preencher manualmente, o que RF-INST-06 quer evitar. Apresentar
um número como "exigência do MED" sem conseguir verificá-lo no texto oficial violaria a
regra do projecto contra fabricação — a sugestão genérica (MAC 30% / Prova Trimestral
30% / Exame 40%, os 3 nomes do próprio exemplo de implementação da issue) é claramente
documentada como não confirmada (`apps/grading/services.py`'s `DEFAULT_EVALUATION_TYPES`)
e o Administrador da Instituição pode alterá-la de imediato.

**Impacto**: `core.services.setup_institution()` chama
`apps.grading.services.seed_default_grading_formula()` logo após criar a Instituição,
activando este valor genérico como fórmula por omissão (não deixando o formulário
vazio) — mas nunca sobrepõe uma fórmula que um Administrador já tenha personalizado.
Se o texto oficial do 106/26 for confirmado no futuro, actualizar
`DEFAULT_EVALUATION_TYPES` e esta nota.

## 2026-09-18 — Issue #27 (expiração de sessão por inactividade): valores concretos

**Contexto**: RNF-SEC-02/§9.2 pede expiração de sessão por inactividade, "mais curta
para perfis administrativos/financeiros", sem indicar valores concretos em minutos.

**Decisão**: `SESSION_TIMEOUT_MINUTES_BY_PROFILE` (`config/settings/base.py`) usa 15
minutos para Super Administrador/Administrador da Instituição/Financeiro/Secretaria
(o contexto da própria issue chama a atenção especificamente para "postos partilhados
da secretaria" — daí incluir Secretaria no grupo mais curto, não só Admin/Financeiro),
30 minutos para Direcção Pedagógica/RH/Director de Turma/Biblioteca, e 60 minutos para
Docente/Encarregado de Educação/Aluno (tipicamente um dispositivo pessoal, não
partilhado). Omissão (perfil não listado): 30 minutos.

**Justificação**: são os únicos números concretos que a documentação não fornece —
qualquer valor exigiria uma escolha; os intervalos escolhidos reflectem directamente a
própria razão dada pela RNF (risco de sessão aberta esquecida num posto partilhado).

**Impacto**: se a instituição quiser afinar estes valores no futuro (ex.: através de
uma UI de configuração), estes tornam-se o ponto de partida por omissão a expor, não
um valor definitivo e imutável.

## 2026-09-18 — Issue #29 (RBAC âmbito por objecto): apenas Encarregado→educandos, por agora

**Contexto**: #29 pede a "matriz completa de §7.2" com verificação de âmbito por
objecto, citando dois exemplos no próprio título: "docente→turmas, encarregado→
educandos".

**Problema**: dos dois, só "encarregado→educandos" tem uma relação real para
restringir por (`enrollment.StudentGuardian`, ligando `Guardian.user` a `Student`).
"Docente→turmas" não tem nenhum dado real para restringir por: `academic.Horario`
(issue #36) e a associação Docente-Disciplina-Turma (issue #85, módulo `hr`) ainda não
existem, e nem sequer `hr.Funcionario` (que ligaria um `User` docente a um registo de
funcionário) foi implementado. Construir esse âmbito agora exigiria fabricar um modelo
de atribuição docente-turma fora do âmbito desta issue, o que as instruções do
projecto proíbem.

**Decisão**: implementar apenas "encarregado→educandos" nesta issue --
`Student`/`Enrollment.objects.for_guardian(user)` (via `StudentQuerySet`/
`EnrollmentQuerySet`, `apps.enrollment.services.get_students_for_guardian`/
`get_enrollments_for_guardian`), mais a permissão `view_student`/`view_enrollment`
para o grupo "Encarregado de Educação" (0004 tinha-o deixado vazio exactamente por
esta razão). "Docente→turmas" fica registado como bloqueado, com um comentário na
própria issue #29 a explicar o porquê e a apontar para #36/#85.

**Impacto**: #29 permanece aberta (não marcada como concluída) até #36/#85
existirem; a issue deve ser revisitada nessa altura para adicionar
`SchoolClass`/`Nota`/`Presenca.objects.for_docente(user)` seguindo exactamente o
mesmo padrão (`TenantQuerySet` subclass + `for_<perfil>()`).
