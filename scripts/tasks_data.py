# -*- coding: utf-8 -*-
"""
Dataset completo de tarefas para o GitHub Project 'FenixSchool' (#11, rickdeu).
Cada entrada gera uma Issue no repo rickdeu/fenixschool, adicionada ao projeto.
Campos: phase (milestone), module (label), priority (P0/P1/P2), size (XS..XL),
title, refs (lista de RF-/RNF-IDs ou secções de doc), context, example, acceptance (lista).
"""

M0 = "M0 - Fundação Técnica"
M1 = "M1 - Fundação"
M2 = "M2 - Núcleo Pedagógico"
M3 = "M3 - Núcleo Financeiro e RH"
M4 = "M4 - Portais e Comunicação"
M5 = "M5 - Offline/Online Completo"
M6 = "M6 - Rede Multi-Escola"
MF = "Futuro - Pós v1"

TASKS = []

def add(module, phase, priority, size, title, refs, context, example, acceptance, doc_links=None):
    TASKS.append(dict(
        module=module, phase=phase, priority=priority, size=size, title=title,
        refs=refs, context=context, example=example, acceptance=acceptance,
        doc_links=doc_links or [],
    ))

# =====================================================================
# M0 — FUNDAÇÃO TÉCNICA / INFRA / ARQUITETURA BASE
# =====================================================================

add("infra", M0, "P0", "M", "Criar estrutura inicial do projeto Django (apps/, config/, templates/, static/, locale/, fixtures/, tests/)",
    ["10.2"],
    "Estabelecer o esqueleto de diretórios definitivo do projeto conforme a estrutura documentada, substituindo o esqueleto mínimo actual gerado por `django-admin startproject`.",
    "```\nfenixschool/\n├── config/settings/{base,local_node,central_node,test}.py\n├── apps/{core,accounts,academic,enrollment,grading,attendance,finance,hr,communications,reports,public_site,student_portal,guardian_portal,admin_panel,sync,api,audit}/\n├── static/{css,js,img}\n├── templates/{base.html,components/}\n├── locale/\n├── fixtures/\n└── tests/{unit,integration,sync_partition}\n```",
    ["Estrutura de diretórios criada e commitada", "`manage.py` e `config/wsgi.py` actualizados para o novo layout", "Projeto arranca com `python manage.py runserver` sem erros"],
    ["10-stack-tecnologica-e-estrutura-projeto.md §10.2"])

add("infra", M0, "P0", "S", "Configurar pyproject.toml com ruff, pytest-django e dependências base",
    ["RNF-MAN-01"],
    "Definir ferramentas de qualidade de código e testes desde o início do projeto.",
    "```toml\n[tool.ruff]\nline-length = 100\n[tool.pytest.ini_options]\nDJANGO_SETTINGS_MODULE = \"config.settings.test\"\n```",
    ["`ruff check .` corre sem erros num projeto vazio", "`pytest` corre e reporta 0 testes coletados sem falhar", "Dependências base (Django, DRF, psycopg) fixadas em requirements/*.txt"],
    ["03-requisitos-nao-funcionais.md §3.9", "10-stack-tecnologica-e-estrutura-projeto.md §10.1"])

add("infra", M0, "P0", "M", "Implementar mixin SyncedModel (UUID v7, instituicao_id, origin_node_id, version, is_deleted, auditoria temporal)",
    ["ADR-03", "ADR-06", "RNF-ESC-03"],
    "Mixin base herdado por toda entidade de negócio, garantindo os campos transversais exigidos para sincronização e auditoria, conforme convenção documentada.",
    "```python\nclass SyncedModel(models.Model):\n    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)\n    instituicao = models.ForeignKey(\"core.Instituicao\", on_delete=models.PROTECT)\n    origin_node_id = models.UUIDField()\n    created_at = models.DateTimeField(auto_now_add=True)\n    updated_at = models.DateTimeField(auto_now=True)\n    updated_by = models.ForeignKey(\"accounts.Utilizador\", null=True, on_delete=models.SET_NULL)\n    version = models.PositiveIntegerField(default=1)\n    is_deleted = models.BooleanField(default=False)\n\n    class Meta:\n        abstract = True\n```",
    ["Mixin abstrato criado em `apps/core/models/base.py`", "UUID v7 gerado correctamente (ordenável por tempo)", "Todos os campos têm índice quando relevante (instituicao_id, is_deleted)", "Testado com um model de exemplo"],
    ["04-arquitetura-tecnica.md §4.5", "05-modelo-de-dados.md (convenções transversais)"])

add("core", M0, "P0", "M", "Implementar TenantQuerySet/Manager com filtragem automática por instituicao_id",
    ["4.4"],
    "Garantir isolamento de dados por instituição em toda a stack (Nó Local e Central), com managers que filtram automaticamente pelo tenant do contexto corrente, e `all_objects` explícito para tarefas de sistema.",
    "```python\nclass TenantQuerySet(models.QuerySet):\n    def for_request(self, request):\n        return self.filter(instituicao_id=request.instituicao_id, is_deleted=False)\n\nclass Modelo(SyncedModel):\n    objects = TenantManager()   # filtra por omissão\n    all_objects = models.Manager()  # sem filtro, uso restrito\n```",
    ["Manager tenant-aware aplicado a todos os models de negócio", "`all_objects` documentado como uso restrito (docstring + code review checklist)", "Teste comprovando que um utilizador da Instituição A nunca vê registos da Instituição B via `objects`"],
    ["04-arquitetura-tecnica.md §4.4"])

add("core", M0, "P0", "M", "Implementar TenantMiddleware (resolve request.instituicao a partir do utilizador autenticado)",
    ["4.4.4"],
    "Middleware que resolve a instituição do pedido a partir do utilizador autenticado, disponibilizando-a a views/services sem que o utilizador tenha de a seleccionar.",
    "```python\nclass TenantMiddleware:\n    def __call__(self, request):\n        if request.user.is_authenticated and not request.user.is_super_admin:\n            request.instituicao = request.user.instituicao\n        return self.get_response(request)\n```",
    ["Middleware regista `request.instituicao` em todo pedido autenticado", "Super Administrador opera num contexto de instituição explicitamente seleccionada para visualização, nunca ambíguo", "Testes cobrindo utilizador normal e Super Administrador"],
    ["04-arquitetura-tecnica.md §4.4.4"])

add("infra", M0, "P0", "S", "Configurar settings divididos (base/local_node/central_node/test)",
    ["10.3"],
    "Separar configuração por ambiente conforme papel do nó (Local vs Central) e por finalidade (testes).",
    "`config/settings/base.py` com o comum; `local_node.py` (Django-Q, sem Celery/Redis); `central_node.py` (Celery+Redis, DRF de sync activo); `test.py` (BD em memória/rápida).",
    ["4 ficheiros de settings criados e a herdar de base.py", "`DJANGO_SETTINGS_MODULE` seleccionável por variável de ambiente", "CI usa `test.py`"],
    ["10-stack-tecnologica-e-estrutura-projeto.md §10.3"])

add("infra", M0, "P0", "M", "Configurar Docker Compose para Nó Local (Postgres + Django/Gunicorn + Nginx + Django-Q)",
    ["11.3"],
    "Empacotar o Nó Local para instalação reprodutível numa escola, sem dependência de Redis.",
    "`docker-compose.local-node.yml` com serviços: `db` (postgres:16), `web` (gunicorn), `nginx`, `qcluster` (django-q worker). Volumes persistentes para dados e backups.",
    ["`docker compose -f docker-compose.local-node.yml up -d` sobe todos os serviços", "Aplicação acessível via Nginx em porta 80/443", "Reinício automático dos serviços (`restart: always`)"],
    ["04-arquitetura-tecnica.md §4.10", "11-implantacao-e-operacoes.md §11.3"])

add("infra", M0, "P1", "M", "Configurar Docker Compose para Nó Central (Postgres + Django + Celery + Redis + Nginx)",
    ["11.2"],
    "Empacotar o Nó Central para agregação multi-instituição, com processamento assíncrono via Celery/Redis.",
    "`docker-compose.central-node.yml` com serviços adicionais: `redis`, `celery-worker`, `celery-beat`.",
    ["Stack central sobe com `docker compose up -d`", "Celery worker processa uma tarefa de teste", "Configuração isolada da do Nó Local (imagens/tags distintas se necessário)"],
    ["11-implantacao-e-operacoes.md §11.2"])

add("infra", M0, "P0", "M", "Configurar pipeline de CI (lint, pip-audit, testes, build Docker)",
    ["13.5", "RNF-MAN-01"],
    "Pipeline de integração contínua que valida qualidade, segurança de dependências e build antes de qualquer merge.",
    "Ver esboço completo em docs/13-testes-e-qualidade.md §13.5 (`.github/workflows/ci.yml`): ruff check, pip-audit, pytest --cov=apps --cov-fail-under=70, docker build.",
    ["Workflow corre em cada push/PR", "Falha o build se cobertura < 70% no núcleo de negócio", "Build da imagem Docker incluído como último passo"],
    ["13-testes-e-qualidade.md §13.5"])

add("infra", M0, "P1", "S", "Configurar WhiteNoise/Nginx para servir estáticos em produção",
    ["4.6"],
    "Garantir que assets (CSS/JS/imagens do frontend integrado) são servidos eficientemente sem CDN externo.",
    "`STATICFILES_STORAGE` com WhiteNoise como fallback local; Nginx a servir `/static/` directamente em produção.",
    ["Ficheiros estáticos servidos com cache-control apropriado", "Nenhuma dependência de CDN externo obrigatória (RNF-COMP-02)"],
    ["04-arquitetura-tecnica.md §4.6", "03-requisitos-nao-funcionais.md §3.6"])

add("core", M0, "P0", "M", "Criar fixtures de referência nacional (Províncias, Municípios, Operadoras Móveis, Tipos de Documento, Profissões)",
    ["5.28", "RNF-LOC-05"],
    "Carregar dados de referência angolanos como fixtures de sistema, disponíveis desde a primeira instalação.",
    "`fixtures/provincias_municipios.json`, `operadoras_moveis.json` (Unitel/Movicel/Africell), `tipos_documento.json` (BI/Cédula/Passaporte/Assento de Nascimento), `profissoes.json`.",
    ["4 fixtures criadas e carregáveis via `loaddata`", "18 províncias angolanas presentes com os respectivos municípios", "Aplicadas automaticamente no setup wizard (ver tarefa dedicada)"],
    ["05-modelo-de-dados.md §5.28", "03-requisitos-nao-funcionais.md §3.7"])

add("infra", M0, "P1", "S", "Configurar django-environ e .env.example",
    ["9.7"],
    "Gerir segredos e configuração sensível fora do código-fonte.",
    "`.env.example` documentando todas as variáveis (SECRET_KEY, DATABASE_URL, NODE_TYPE, etc.), nunca com valores reais commitados.",
    ["`.env.example` completo e comentado", "`.env` real no `.gitignore`", "Settings lêem tudo via `environ.Env()`"],
    ["09-seguranca-e-privacidade.md §9.7"])

add("infra", M0, "P1", "S", "Configurar logging estruturado local (django-structlog)",
    ["RNF-OBS-01"],
    "Logs estruturados e rotacionados automaticamente, sem depender de serviço externo, essencial para diagnóstico offline.",
    "`django-structlog` com renderer JSON em produção e rotação via `logging.handlers.TimedRotatingFileHandler`.",
    ["Logs em formato estruturado (JSON) gravados localmente", "Rotação automática configurada (ex. diária, retenção 30 dias)"],
    ["03-requisitos-nao-funcionais.md §3.11"])

add("infra", M0, "P2", "S", "Configurar Sentry auto-hospedado opcional para o Nó Central",
    ["RNF-OBS-03"],
    "Reportar erros de aplicação quando há conectividade, sem bloquear a operação offline do Nó Local.",
    "Integração `sentry-sdk` activada apenas quando `SENTRY_DSN` está definida; nunca obrigatória para o Nó Local arrancar.",
    ["Erros capturados no Nó Central quando configurado", "Ausência de DSN não impede arranque nem gera erro"],
    ["03-requisitos-nao-funcionais.md §3.11"])

# =====================================================================
# CORE app
# =====================================================================

add("core", M1, "P0", "M", "Model Instituicao completo + Django Admin",
    ["RF-INST-01", "5.2"],
    "Entidade central que representa a instituição de ensino, com todos os dados administrativos, de contacto e de parametrização.",
    "Campos: nome, nif, codigo_med, provincia, municipio, distrito_comuna, bairro, rua, numero_casa, telefone_fixo/unitel/movicel/africell, email, website, logotipo, ano_lectivo_corrente, formula_media_default (JSON), bloqueia_documentos_com_divida.",
    ["Model criado com todos os campos de 05-modelo-de-dados.md §5.2", "Registado no Django Admin", "Migração aplicada e testada"],
    ["05-modelo-de-dados.md §5.2"])

add("core", M1, "P0", "M", "Models AnoLectivo, PeriodoLectivo, CicloLectivo e DiaNaoLectivo + Admin",
    ["RF-INST-03", "RF-INST-04", "RF-INST-05", "RF-INST-07", "5.3"],
    "Estrutura temporal do calendário escolar angolano: ano lectivo, períodos (trimestres/semestres), ciclos e feriados/dias não lectivos.",
    "`AnoLectivo(designacao, data_inicio, data_fim, is_corrente)`, `PeriodoLectivo(ano_lectivo, numero, data_inicio, data_fim)`, `CicloLectivo(designacao, ordem)`, `DiaNaoLectivo(data, descricao, abrangencia)`.",
    ["4 models criados e registados no Admin", "Apenas um AnoLectivo pode ser `is_corrente=True` por instituição (constraint/validação)", "Testes de validação de datas (período dentro do ano lectivo)"],
    ["05-modelo-de-dados.md §5.3"])

add("core", M1, "P0", "M", "Setup Wizard: criação de Instituição + Gestor na mesma transação",
    ["4.4.2", "11.3"],
    "Único ponto do sistema em que a instituição é explicitamente criada/seleccionada para um utilizador — acontece uma única vez, na instalação inicial do Nó Local.",
    "Fluxo (ver sequenceDiagram em 04-arquitetura-tecnica.md §4.4.2): formulário único captura dados da Instituição + dados do Gestor; `transaction.atomic()` cria ambos; carrega fixtures nacionais; gera `Node.id` local.",
    ["Wizard acessível apenas quando não existe nenhuma Instituição no Nó Local", "Instituição e Gestor criados atomically (falha de um reverte o outro)", "Após conclusão, wizard fica inacessível/redireciona para login"],
    ["04-arquitetura-tecnica.md §4.4.2", "11-implantacao-e-operacoes.md §11.3"])

add("core", M1, "P0", "S", "Serviço de configuração da fórmula de cálculo de média (formula_media_default)",
    ["RF-INST-06"],
    "Permitir parametrizar por instituição (e sobrepor por curso/disciplina) os pesos de MAC/PT/Exame na fórmula de média final.",
    "```python\ndef calcular_media(notas: list[Nota], formula: dict) -> Decimal:\n    return sum(n.classificacao * formula[n.tipo_avaliacao.designacao] for n in notas)\n```\nUI de configuração em `admin_panel` com pré-visualização do cálculo.",
    ["Fórmula editável pelo Administrador da Instituição", "Sobreposição possível ao nível de curso/disciplina", "Validação: soma dos pesos = 1 (ou 100%)"],
    ["02-requisitos-funcionais.md RF-INST-06", "05-modelo-de-dados.md §5.2"])

add("core", M1, "P1", "S", "Tela de configuração de tabelas de preços por ano lectivo/curso/classe",
    ["RF-INST-08"],
    "Parametrização de propinas, emolumentos e taxas, base para o módulo financeiro.",
    "Formulário CRUD em `core`/`finance` para `TabelaPrecos` (ver tarefa dedicada em finance), acessível apenas ao perfil Financeiro/Admin.",
    ["Tabela de preços configurável por ano lectivo e curso/classe", "Histórico de alterações preservado (nunca sobrescrito silenciosamente)"],
    ["02-requisitos-funcionais.md RF-INST-08"])

add("core", M1, "P1", "S", "Tela de configuração de feriados e dias não lectivos",
    ["RF-INST-07"],
    "Permitir à instituição registar feriados nacionais/provinciais e dias não lectivos próprios, usados no cálculo de assiduidade e calendário.",
    "CRUD simples de `DiaNaoLectivo` com filtro por abrangência (nacional/provincial/institucional); pré-carregar feriados nacionais conhecidos como fixture inicial.",
    ["Feriados nacionais pré-carregados na instalação", "Instituição pode adicionar dias não lectivos próprios", "Calendário público (RF-PUB) reflecte estes dados"],
    ["02-requisitos-funcionais.md RF-INST-07"])

# =====================================================================
# ACCOUNTS app
# =====================================================================

add("accounts", M1, "P0", "L", "Model Utilizador customizado (AbstractUser) com instituicao, criado_por, idioma_preferido, 2FA flag",
    ["4.4.1", "5.24", "RNF-LOC-07"],
    "Utilizador base de autenticação de todo o sistema, com o campo `instituicao` definido uma única vez na criação e nunca editável por formulário normal.",
    "```python\nclass Utilizador(AbstractUser):\n    instituicao = models.ForeignKey(\"core.Instituicao\", null=True, on_delete=models.PROTECT)\n    criado_por = models.ForeignKey(\"self\", null=True, on_delete=models.SET_NULL)\n    telefone = models.CharField(max_length=20, blank=True)\n    idioma_preferido = models.CharField(max_length=8, choices=LANGUAGES, default=\"pt\")\n    is_2fa_ativo = models.BooleanField(default=False)\n```",
    ["`AUTH_USER_MODEL` apontado para este model", "Campo `instituicao` não editável via formulário de edição de perfil", "Migração inicial testada com createsuperuser"],
    ["04-arquitetura-tecnica.md §4.4.1", "05-modelo-de-dados.md §5.24"])

add("accounts", M1, "P0", "M", "Model Perfil/Grupo com os 12 perfis definidos + fixture de setup",
    ["7.1"],
    "Perfis de acesso ao sistema, implementados como Django Groups com permissões associadas.",
    "Fixture criando os grupos: Super Administrador, Administrador da Instituição, Direção Pedagógica, Secretaria Escolar, Financeiro/Tesouraria, Recursos Humanos, Docente, Diretor de Turma, Biblioteca, Encarregado de Educação, Aluno, Público.",
    ["12 grupos criados via migração de dados/fixture", "Cada grupo com o conjunto de permissões Django correspondente à matriz de 07-perfis-permissoes-e-fluxos.md §7.2"],
    ["07-perfis-permissoes-e-fluxos.md §7.1-7.2"])

add("accounts", M1, "P0", "M", "Serviço criar_utilizador() com propagação automática de tenant",
    ["4.4.1"],
    "Regra de negócio central: todo utilizador criado por outro (excepto Super Administrador) herda automaticamente a instituição de quem o criou — nunca há campo 'Escola' visível no formulário.",
    "```python\ndef criar_utilizador(dados, criado_por):\n    instituicao = dados[\"instituicao\"] if criado_por.is_super_admin else criado_por.instituicao\n    return Utilizador.objects.create(instituicao=instituicao, criado_por=criado_por, **dados)\n```",
    ["Função implementada em `apps/accounts/services.py`", "Teste comprovando herança automática para Secretaria/Docente/RH/Financeiro criados pelo Gestor", "Teste comprovando que só Super Administrador escolhe instituição explicitamente"],
    ["04-arquitetura-tecnica.md §4.4.1 (pseudo-código incluído)"])

add("accounts", M1, "P0", "M", "Login sem seleção de escola (view + template)",
    ["4.4.4", "9.2"],
    "Ecrã de autenticação simples: email/telefone + password, sem qualquer campo ou dropdown de instituição.",
    "View de login Django padrão customizada; após autenticação, `TenantMiddleware` resolve a instituição automaticamente.",
    ["Formulário de login sem campo de instituição", "Redireciona ao dashboard correcto consoante o perfil", "Mensagens de erro em português claro (RNF-USA-01)"],
    ["04-arquitetura-tecnica.md §4.4.4", "09-seguranca-e-privacidade.md §9.2"])

add("accounts", M1, "P0", "M", "2FA (TOTP) obrigatório para Administrador, Super Administrador e Financeiro",
    ["RNF-SEC-05", "9.2"],
    "Autenticação de dois factores que funciona offline (TOTP não depende de SMS/rede), obrigatória para perfis de maior risco.",
    "`django-otp` com `TOTPDevice`; middleware que exige 2FA configurado antes de aceder a áreas administrativas/financeiras.",
    ["2FA obrigatório bloqueia acesso até ser configurado, para os 3 perfis indicados", "QR code de configuração gerado no primeiro login", "Testado sem ligação à Internet (TOTP local)"],
    ["03-requisitos-nao-funcionais.md RNF-SEC-05", "09-seguranca-e-privacidade.md §9.2"])

add("accounts", M1, "P0", "S", "Política de password (Argon2, bloqueio progressivo após tentativas falhadas)",
    ["RNF-SEC-02", "9.2"],
    "Reforço de segurança de autenticação sem exigir complexidade artificial excessiva.",
    "`PASSWORD_HASHERS` com Argon2 primeiro; `django-axes` ou lógica própria de bloqueio progressivo com desbloqueio administrativo.",
    ["Passwords nunca guardadas em texto plano, mesmo localmente", "Conta bloqueada após N tentativas falhadas", "Administrador consegue desbloquear manualmente"],
    ["03-requisitos-nao-funcionais.md RNF-SEC-02", "09-seguranca-e-privacidade.md §9.2"])

add("accounts", M1, "P1", "S", "Sessões com expiração automática por inactividade, configurável por perfil",
    ["9.2"],
    "Reduzir risco de sessões abertas esquecidas, sobretudo em postos partilhados da secretaria.",
    "`SESSION_COOKIE_AGE` diferenciado por grupo via middleware customizado, mais curto para Admin/Financeiro.",
    ["Sessão expira automaticamente após período configurado", "Período configurável por perfil"],
    ["09-seguranca-e-privacidade.md §9.2"])

add("accounts", M1, "P0", "S", "Seletor de idioma pessoal no cabeçalho (idioma_preferido)",
    ["RF-I18N-02", "RNF-LOC-07"],
    "Cada utilizador escolhe e altera o seu próprio idioma de interface, independente dos restantes utilizadores da mesma instituição.",
    "Dropdown no cabeçalho (Alpine.js) que faz POST para actualizar `idioma_preferido` e recarrega com `translation.activate()`.",
    ["Idioma alterável em qualquer momento pelo próprio utilizador", "Preferência persistida e aplicada em pedidos futuros", "Nenhuma configuração equivalente ao nível da instituição"],
    ["03-requisitos-nao-funcionais.md RF-I18N-02/RNF-LOC-07", "10-stack-tecnologica-e-estrutura-projeto.md §10.4"])

add("accounts", M1, "P0", "M", "RBAC: Groups/Permissions + verificação de âmbito por objeto (docente→turmas, encarregado→educandos)",
    ["7.2", "RNF-SEC-03"],
    "Reforçar a matriz de permissões por módulo com verificações ao nível do objecto: um docente só vê/edita notas das suas turmas; um encarregado só vê os seus educandos.",
    "QuerySets filtrados por perfil em cada `service` (ex. `Nota.objects.for_docente(user)` filtra por `Horario` associado); testes por perfil.",
    ["Matriz completa de 07-perfis-permissoes-e-fluxos.md §7.2 implementada", "Testes automatizados por perfil confirmando âmbito correcto", "Nenhum acesso cruzado entre docentes/turmas ou encarregados/alunos não associados"],
    ["07-perfis-permissoes-e-fluxos.md §7.2"])

# =====================================================================
# ACADEMIC app
# =====================================================================

add("academic", M1, "P0", "S", "Model Departamento + Admin", ["RF-CURR-01", "5.4"],
    "Entidade responsável pela gestão das disciplinas de um curso, com responsável associado.",
    "`Departamento(nome, responsavel: FK Funcionario)`.",
    ["Model criado e registado no Admin", "CRUD funcional via `academic`"],
    ["05-modelo-de-dados.md §5.4"])

add("academic", M1, "P0", "M", "Model Curso + Admin", ["RF-CURR-02", "5.5"],
    "Conjunto de disciplinas que conferem um grau académico, com código MED e ciclo associado.",
    "`Curso(codigo, nome, abreviatura, data_criacao, departamento, codigo_med, ciclo, duracao_anos)`.",
    ["Model criado com todos os campos de 05-modelo-de-dados.md §5.5", "Validação de código único por instituição"],
    ["05-modelo-de-dados.md §5.5"])

add("academic", M1, "P0", "M", "Model Disciplina + Admin", ["RF-CURR-03", "5.6"],
    "Disciplinas associadas a curso e ano curricular, com tipo, ciclo e carga horária.",
    "`Disciplina(codigo, nome, abreviatura, curso, ano_curricular, periodo, ciclo, tipo_disciplina, carga_horaria_semanal)`.",
    ["Model criado e testado", "Tipo de disciplina (obrigatória/opcional/extracurricular) impacta cálculo de situação final (integração futura com grading)"],
    ["05-modelo-de-dados.md §5.6"])

add("academic", M1, "P0", "S", "Model AnoCurricular + Admin", ["RF-CURR-04", "5.7"],
    "Separação entre ano do curso (1.º a 4.º) e classe administrativa (10.ª a 13.ª), essencial para alunos repetentes.",
    "`AnoCurricular(curso, numero, classe_equivalente)`.",
    ["Model criado", "Suporta correctamente aluno repetente na mesma classe em anos lectivos diferentes"],
    ["05-modelo-de-dados.md §5.7"])

add("academic", M1, "P0", "M", "Model Turma + Admin (com limites legais de lotação por omissão)", ["RF-CURR-05", "5.8"],
    "Agrupamento de alunos por curso/ano curricular/ano lectivo, com lotação por omissão baseada no Decreto Presidencial 162/23.",
    "`Turma(codigo, designacao, ano_lectivo, periodo_lectivo, curso, ano_curricular, numero_maximo_inscritos=36, director_turma, turno)`.",
    ["Lotação por omissão 36 (configurável até 45/26 conforme legislação)", "Model registado no Admin com filtros por ano lectivo"],
    ["05-modelo-de-dados.md §5.8", "docs/legislacao/README.md (Decreto 162/23)"])

add("academic", M1, "P1", "S", "Model Sala + Admin", ["RF-CURR-07", "5.9"],
    "Salas de aula com capacidade, usadas na gestão de horários.",
    "`Sala(designacao, capacidade)`.",
    ["Model criado", "Usado na validação de conflito de horário (capacidade vs turma, opcional)"],
    ["05-modelo-de-dados.md §5.9"])

add("academic", M2, "P0", "M", "Model Horario + Admin", ["RF-CURR-06", "5.10"],
    "Grelha horária por turma: dia, hora, regime, sala, docente, disciplina.",
    "`Horario(turma, disciplina, dia_semana, hora_inicio, hora_fim, regime, sala, docente)`.",
    ["Model criado e testado", "Base para associação de docentes a turmas (RF-RH-02) e para presença/faltas (attendance)"],
    ["05-modelo-de-dados.md §5.10"])

add("academic", M2, "P0", "M", "Serviço validar_conflito_horario (deteção de sobreposição docente/sala/turma)", ["RF-CURR-06"],
    "Impedir a criação de horários com sobreposição para o mesmo docente, sala ou turma no mesmo intervalo de tempo.",
    "```python\ndef validar_conflito_horario(novo: Horario):\n    conflitos = Horario.objects.filter(\n        Q(docente=novo.docente) | Q(sala=novo.sala) | Q(turma=novo.turma),\n        dia_semana=novo.dia_semana,\n    ).exclude(pk=novo.pk)\n    for h in conflitos:\n        if intervalos_sobrepostos(h, novo):\n            raise ConflitoHorarioError(h)\n```",
    ["Função implementada em `apps/academic/services.py`", "Testes cobrindo conflito de docente, de sala e de turma", "Mensagem de erro identifica o horário em conflito"],
    ["02-requisitos-funcionais.md RF-CURR-06"])

add("academic", M2, "P1", "S", "Mapa de ocupação de salas e docentes (view)", ["6.5"],
    "Visualização semanal de ocupação, útil para planeamento pela Direção Pedagógica.",
    "View com grelha semana × sala (ou docente), reutilizando os dados de `Horario`.",
    ["Mapa visual acessível a Direção Pedagógica/Admin", "Filtro por sala, docente ou turma"],
    ["06-modulos-e-funcionalidades.md §6.5"])

# =====================================================================
# ENROLLMENT app
# =====================================================================

add("enrollment", M1, "P0", "L", "Model Aluno completo + Admin", ["RF-MAT-02", "5.11"],
    "Entidade correspondente ao acto de Inscrição: dados pessoais, documento, endereço, contactos, estado.",
    "Campos completos conforme 05-modelo-de-dados.md §5.11, incluindo `numero_aluno` sequencial por instituição.",
    ["Model criado com todos os campos", "`numero_aluno` gerado automaticamente e sequencial por instituição", "Documento de identificação suporta BI/Cédula/Passaporte/Assento de Nascimento"],
    ["05-modelo-de-dados.md §5.11"])

add("enrollment", M1, "P0", "M", "Model EncarregadoEducacao + Admin", ["5.12"],
    "Figura legal e financeiramente responsável pelo aluno, com conta de acesso opcional ao portal.",
    "`EncarregadoEducacao(nome_completo, grau_parentesco, tipo/numero_documento, contactos, endereco, utilizador FK opcional 1-1)`.",
    ["Model criado", "Ligação opcional a `Utilizador` para acesso ao portal"],
    ["05-modelo-de-dados.md §5.12"])

add("enrollment", M1, "P0", "S", "Model EncarregadoAluno (tabela associativa) + regra de encarregado principal", ["RF-MAT-11", "5.13"],
    "Permite múltiplos encarregados por aluno (ex. pai e mãe) com indicação de principal para comunicação/financeiro.",
    "`EncarregadoAluno(aluno, encarregado, is_principal, responsavel_financeiro)` com constraint de um único `is_principal=True` por aluno.",
    ["Model criado com constraint de unicidade do principal", "Suporta múltiplos encarregados por aluno"],
    ["02-requisitos-funcionais.md RF-MAT-11", "05-modelo-de-dados.md §5.13"])

add("enrollment", M1, "P1", "M", "Model Candidato + fluxo de pré-candidatura", ["RF-MAT-10", "5.14"],
    "Registo e gestão de candidatos antes da inscrição efectiva, alimentado também pelo portal público.",
    "`Candidato(nome_completo, data_nascimento, curso_pretendido, contacto, estado, data_candidatura)`; fluxo de admissão que converte Candidato em Aluno.",
    ["Model criado", "Acção 'Admitir' converte candidato em inscrição de aluno, pré-preenchendo dados"],
    ["02-requisitos-funcionais.md RF-MAT-10", "05-modelo-de-dados.md §5.14"])

add("enrollment", M1, "P0", "L", "Model Matricula completo + Admin", ["RF-MAT-05", "5.15"],
    "Acto anual que associa o aluno a curso/turma/ano lectivo, distinto da inscrição.",
    "Campos completos de 05-modelo-de-dados.md §5.15, incluindo `estado_matricula`, `is_repetente`, `matricula_anterior`.",
    ["Model criado com todos os campos", "`numero_matricula` sequencial por instituição/ano", "Estados suportados: Pendente/Activa/Anulada/Transferida/Concluída"],
    ["05-modelo-de-dados.md §5.15"])

add("enrollment", M1, "P0", "M", "Serviço inscrever_aluno() com validação anti-duplicação por documento", ["RF-MAT-01", "RF-MAT-03"],
    "Regra de negócio central: a inscrição é única e perpétua; o sistema impede duplicação pelo número de documento de identificação.",
    "```python\ndef inscrever_aluno(dados):\n    if Aluno.objects.filter(numero_documento=dados[\"numero_documento\"]).exists():\n        raise AlunoJaInscritoError()\n    return Aluno.objects.create(numero_aluno=proximo_numero(instituicao), **dados)\n```",
    ["Duplicação por documento bloqueada com mensagem clara ao operador", "Número de aluno atribuído automaticamente e nunca reutilizado", "Teste replicando o exemplo do documento original (aluna Yolene Hangalo)"],
    ["02-requisitos-funcionais.md RF-MAT-01/03", "06-modulos-e-funcionalidades.md §6.4"])

add("enrollment", M1, "P0", "L", "Fluxo de Inscrição (view/template): formulário completo com foto, documento, endereço, encarregado", ["RF-MAT-02", "6.4"],
    "Ecrã principal de Inscrição, reproduzindo e modernizando o formulário do sistema original (Novo Aluno).",
    "Formulário multi-secção (Dados Pessoais / Endereço / Contactos / Encarregado de Educação) com upload de foto; associação a Encarregado novo ou existente (busca por documento).",
    ["Formulário cobre todos os campos de RF-MAT-02", "Permite associar encarregado novo ou já existente", "Consentimento do encarregado (checkbox + timestamp) registado — RNF-AUD-02"],
    ["06-modulos-e-funcionalidades.md §6.4", "09-seguranca-e-privacidade.md §9.1"])

add("enrollment", M1, "P0", "M", "Serviço matricular_aluno() com validação de vaga disponível", ["RF-MAT-07"],
    "Impedir matrícula em turma já lotada, validando contra `numero_maximo_inscritos`.",
    "```python\ndef matricular_aluno(aluno, turma, ...):\n    if turma.matriculas_activas().count() >= turma.numero_maximo_inscritos:\n        raise TurmaLotadaError(turma)\n    return Matricula.objects.create(aluno=aluno, turma=turma, ...)\n```",
    ["Matrícula bloqueada quando turma está lotada, com mensagem clara", "Teste de fronteira (última vaga disponível)"],
    ["02-requisitos-funcionais.md RF-MAT-07"])

add("enrollment", M1, "P0", "L", "Fluxo de Matrícula (view/template): busca aluno, seleção curso/turma/ano, guardar e imprimir", ["RF-MAT-04", "RF-MAT-05", "RF-MAT-06", "6.4"],
    "Reproduz o fluxo do documento original: busca por número/documento, pré-carregamento de dados, selecção de curso/turma/ciclo/ano curricular, botão 'Guardar e Imprimir'.",
    "Busca com HTMX (resultado em tabela + botão Matricular por linha); modal/formulário de matrícula pré-carregado com dados do aluno.",
    ["Busca funciona por número de aluno, documento ou nome", "Botão 'Guardar e Imprimir' grava a matrícula e dispara geração do PDF (tarefa dedicada)", "Fluxo idêntico em espírito ao demonstrado no documento original"],
    ["06-modulos-e-funcionalidades.md §6.4 (fluxo completo)"])

add("enrollment", M2, "P0", "S", "Geração de comprovativo de matrícula em PDF", ["RF-MAT-06"],
    "Emitir comprovativo imprimível imediatamente após confirmação da matrícula.",
    "Template HTML renderizado via WeasyPrint, reaproveitando o template de ecrã da matrícula.",
    ["PDF gerado automaticamente ao gravar a matrícula", "Inclui todos os dados relevantes e é imprimível em A4"],
    ["02-requisitos-funcionais.md RF-MAT-06"])

add("enrollment", M2, "P1", "M", "Fluxo de transferência de aluno (turma/curso/instituição) preservando histórico", ["RF-MAT-08"],
    "Permitir mover um aluno entre turmas/cursos ou mesmo instituições sem perder o histórico académico.",
    "Serviço `transferir_aluno()` que cria nova Matrícula referenciando a anterior e marca a antiga como 'Transferida'.",
    ["Histórico do aluno preservado após transferência", "Transferência entre instituições da mesma rede transita via Nó Central (4.4.3)"],
    ["02-requisitos-funcionais.md RF-MAT-08"])

add("enrollment", M2, "P0", "S", "Fluxo de matrícula de aluno repetente vinculado ao histórico anterior", ["RF-MAT-09"],
    "Suportar retenção de ano, ligando a nova matrícula à do ano lectivo anterior.",
    "Campo `is_repetente` + `matricula_anterior` preenchidos no fluxo de matrícula quando aplicável.",
    ["Matrícula de repetente correctamente vinculada à anterior", "Situação reflectida em relatórios e histórico escolar"],
    ["02-requisitos-funcionais.md RF-MAT-09"])

add("enrollment", M2, "P1", "S", "Fluxo de anulação de matrícula com motivo obrigatório", ["6.4"],
    "Permitir anular uma matrícula (ex. desistência), preservando o registo com motivo e auditoria.",
    "Acção 'Anular' muda `estado_matricula` para Anulada e exige campo de motivo preenchido; nunca elimina o registo (soft-delete/estado).",
    ["Anulação exige motivo preenchido", "Matrícula anulada permanece consultável no histórico"],
    ["06-modulos-e-funcionalidades.md §6.4"])

add("enrollment", M1, "P0", "S", "Suporte a um encarregado associado a múltiplos alunos com login único", ["RF-MAT-12"],
    "Um encarregado com vários educandos na instituição deve aceder a todos com uma única conta.",
    "Portal do encarregado lista todos os `EncarregadoAluno` do utilizador autenticado, com selector de educando quando há mais de um.",
    ["Um único login dá acesso a todos os educandos do encarregado", "Selector de educando visível apenas quando aplicável (mais de um filho)"],
    ["02-requisitos-funcionais.md RF-MAT-12"])

add("enrollment", M3, "P1", "S", "Emissão de declaração de matrícula a qualquer momento", ["6.4"],
    "Permitir à Secretaria emitir uma declaração de matrícula fora do fluxo inicial, sempre que solicitado.",
    "Reaproveita o gerador de documentos oficiais (app `reports`) com o template de Declaração de Matrícula.",
    ["Declaração emitível a qualquer momento pela Secretaria", "Inclui numeração/série única (RF-REL-06)"],
    ["06-modulos-e-funcionalidades.md §6.4"])

# =====================================================================
# GRADING app
# =====================================================================

add("grading", M2, "P0", "S", "Model TipoAvaliacao + fixture (MAC, Prova Trimestral, Exame)", ["5.16"],
    "Parametriza os componentes usados na fórmula de média.",
    "`TipoAvaliacao(designacao, peso_default)` com fixture inicial MAC/PT/Exame.",
    ["Model criado", "Fixture inicial carregada na instalação"],
    ["05-modelo-de-dados.md §5.16"])

add("grading", M2, "P0", "L", "Model Nota completo + Admin", ["RF-AVAL-01", "5.17"],
    "Registo de classificação por aluno/disciplina/período/tipo de avaliação, com bloqueio por pauta fechada.",
    "Campos completos de 05-modelo-de-dados.md §5.17, incluindo `is_pauta_fechada`.",
    ["Model criado com todos os campos", "Edição bloqueada quando `is_pauta_fechada=True` sem autorização"],
    ["05-modelo-de-dados.md §5.17"])

add("grading", M2, "P0", "M", "Fixture EscalaAvaliacao oficial (Decreto Executivo 106/26)", ["RF-AVAL-03"],
    "Carregar a escala oficial de avaliação do Ensino Secundário (0–20, níveis Excelente a Mau) como dado de sistema.",
    "Fixture `escala_avaliacao.json` com os 5 níveis e intervalos de docs/legislacao/escala-avaliacao-secundario.md.",
    ["Fixture carregada e usada para apresentar o nível qualitativo junto da nota numérica", "Editável apenas por Super Administrador (parâmetro normativo nacional)"],
    ["docs/legislacao/escala-avaliacao-secundario.md"])

add("grading", M2, "P0", "M", "Serviço lancar_nota() com validação de escala 0-20 e nível qualitativo", ["RF-AVAL-01", "RF-AVAL-03"],
    "Lançamento de notas por docente, validando limites e apresentando o nível qualitativo correspondente.",
    "```python\ndef lancar_nota(docente, aluno, disciplina, tipo_avaliacao, classificacao):\n    if not (0 <= classificacao <= 20):\n        raise NotaForaDaEscalaError()\n    nivel = EscalaAvaliacao.objects.nivel_para(classificacao)\n    return Nota.objects.create(..., classificacao=classificacao)\n```",
    ["Validação de escala aplicada em todos os pontos de entrada", "Nível qualitativo mostrado junto ao valor numérico", "Apenas docente associado à turma/disciplina pode lançar (RBAC)"],
    ["02-requisitos-funcionais.md RF-AVAL-01/03"])

add("grading", M2, "P0", "L", "Motor de cálculo de média parametrizada", ["RF-AVAL-02", "RF-INST-06"],
    "Calcular automaticamente a média/classificação final segundo a fórmula configurada, com possibilidade de ajuste manual justificado.",
    "Reaproveita `formula_media_default` (ou sobreposição por curso/disciplina) para calcular a média a partir das notas por tipo de avaliação.",
    ["Cálculo automático correcto para os casos de teste da fórmula configurada", "Ajuste manual exige justificação registada em auditoria"],
    ["02-requisitos-funcionais.md RF-AVAL-02"])

add("grading", M2, "P0", "L", "Grelha de lançamento de notas via HTMX (por turma/disciplina/período)", ["6.6"],
    "Interface eficiente para o docente lançar notas de uma turma inteira sem recarregar a página a cada gravação.",
    "Tabela HTMX com `hx-post` por célula/linha, feedback imediato de gravação e validação inline.",
    ["Lançamento linha-a-linha sem reload completo da página", "Feedback visual de sucesso/erro por célula"],
    ["06-modulos-e-funcionalidades.md §6.6"])

add("grading", M2, "P0", "M", "Fluxo de fecho/homologação de pauta (fechar_pauta) com reabertura restrita", ["RF-AVAL-04", "7.4"],
    "Bloquear alterações após homologação da Direção Pedagógica, com auditoria de quem fechou/reabriu.",
    "Sequência completa em 07-perfis-permissoes-e-fluxos.md §7.4: docente submete → Direção homologa → `is_pauta_fechada=True` → reabertura exige justificação.",
    ["Pauta bloqueada após homologação", "Reabertura só por Direção Pedagógica, com justificação obrigatória e registo de auditoria"],
    ["07-perfis-permissoes-e-fluxos.md §7.4"])

add("grading", M2, "P1", "M", "Fluxo de avaliação de recurso/recuperação/exame especial", ["RF-AVAL-06"],
    "Suportar avaliações extraordinárias que impactam a situação final do aluno.",
    "`TipoAvaliacao` adicional 'Exame de Recurso'; regra de recálculo da situação final quando presente.",
    ["Nota de recurso correctamente ponderada na situação final", "Estado 'Em recurso' suportado até resolução"],
    ["02-requisitos-funcionais.md RF-AVAL-06"])

add("grading", M2, "P0", "L", "Cálculo automático da situação final do aluno no ano lectivo", ["RF-AVAL-07"],
    "Determinar aprovado/reprovado/disciplinas em atraso com base nas médias de todas as disciplinas do ano curricular.",
    "Serviço `calcular_situacao_final(matricula)` percorrendo todas as disciplinas do ano curricular e aplicando a nota mínima (10 valores).",
    ["Situação calculada correctamente para casos de aprovação total, reprovação e disciplinas em atraso", "Resultado usado em relatórios e no portal do aluno/encarregado"],
    ["02-requisitos-funcionais.md RF-AVAL-07"])

add("grading", M3, "P0", "M", "Histórico escolar consolidado por aluno (todos os anos lectivos)", ["RF-AVAL-08"],
    "Consulta consolidada de todo o percurso escolar do aluno, mesmo após transferência ou conclusão.",
    "View agregando todas as `Matricula`/`Nota` do aluno, ordenadas por ano lectivo.",
    ["Histórico completo acessível mesmo para alunos transferidos/concluídos", "Inclui todas as disciplinas e médias de cada ano lectivo"],
    ["02-requisitos-funcionais.md RF-AVAL-08"])

add("grading", M2, "P0", "M", "Geração de Pautas por turma/disciplina/período e Boletins por aluno", ["RF-AVAL-05"],
    "Documentos consolidados de resultados, base para os documentos oficiais (app reports).",
    "Views/templates de Pauta (grelha turma×disciplina) e Boletim (extracto individual), reaproveitados pelo gerador de PDF em `reports`.",
    ["Pauta e Boletim gerados correctamente a partir das notas lançadas", "Integração com app `reports` para exportação em PDF"],
    ["02-requisitos-funcionais.md RF-AVAL-05"])

# =====================================================================
# ATTENDANCE app
# =====================================================================

add("attendance", M2, "P0", "M", "Model Presenca + Admin", ["RF-FREQ-01", "5.18"],
    "Registo de presença/falta por aula, ligado ao horário do dia.",
    "`Presenca(aluno, horario, data, estado, justificacao_texto, justificacao_anexo, registado_por)`.",
    ["Model criado com todos os campos", "Estado suporta Presente/Falta/Falta Justificada"],
    ["05-modelo-de-dados.md §5.18"])

add("attendance", M2, "P0", "M", "Serviço de registo de presença/falta por aula", ["RF-FREQ-01"],
    "Permitir ao docente marcar presenças rapidamente a partir do horário do dia.",
    "View com lista de alunos da turma pré-carregada a partir do `Horario` do dia, marcação em lote via HTMX.",
    ["Marcação de turma inteira em poucos cliques", "Apenas docente da disciplina/turma pode registar (RBAC)"],
    ["02-requisitos-funcionais.md RF-FREQ-01"])

add("attendance", M2, "P1", "S", "Fluxo de justificação de faltas com anexo opcional", ["RF-FREQ-02"],
    "Permitir registar justificação de uma falta, com documento comprovativo opcional.",
    "Formulário associado a `Presenca` existente, upload de anexo armazenado com acesso mediado pela aplicação (nunca URL pública directa).",
    ["Justificação registável com ou sem anexo", "Anexo acessível apenas a utilizadores autorizados"],
    ["02-requisitos-funcionais.md RF-FREQ-02", "09-seguranca-e-privacidade.md §9.3"])

add("attendance", M2, "P0", "M", "Cálculo de percentagem de assiduidade e alerta de limite legal (3× carga semanal)", ["RF-FREQ-03"],
    "Alertar quando o aluno ultrapassa o limite de faltas injustificadas permitido por lei (Decreto Presidencial 162/23), parametrizável por instituição.",
    "Serviço que calcula faltas acumuladas por disciplina/período e compara com `limite_faltas = 3 * carga_horaria_semanal` (valor por omissão configurável).",
    ["Cálculo correcto de percentagem de assiduidade", "Alerta accionado ao ultrapassar o limite, com impacto sinalizado na situação final"],
    ["02-requisitos-funcionais.md RF-FREQ-03", "docs/legislacao/README.md (Decreto 162/23)"])

add("attendance", M2, "P1", "S", "Mapa de faltas por turma, docente e encarregado de educação", ["RF-FREQ-04"],
    "Consulta de faltas em diferentes granularidades e perfis.",
    "Views de listagem filtráveis por turma/docente; no portal do encarregado, filtrado automaticamente ao(s) seu(s) educando(s).",
    ["Mapa de faltas disponível para Direção/Docente/Encarregado, cada um com o âmbito correcto"],
    ["02-requisitos-funcionais.md RF-FREQ-04"])

# =====================================================================
# FINANCE app
# =====================================================================

add("finance", M3, "P0", "M", "Model TabelaPrecos + Admin", ["RF-FIN-01"],
    "Parametrização de propinas, emolumentos e taxas por ano lectivo/curso/classe.",
    "`TabelaPrecos(ano_lectivo, curso, classe, tipo_taxa, valor, data_vigencia)`.",
    ["Model criado", "CRUD acessível ao perfil Financeiro/Admin"],
    ["02-requisitos-funcionais.md RF-FIN-01"])

add("finance", M3, "P0", "L", "Model Mensalidade completo + Admin", ["5.19"],
    "Plano de mensalidades do aluno por mês/ano lectivo, com valor devido/pago/juro e estado.",
    "Campos completos de 05-modelo-de-dados.md §5.19, incluindo `valor_devido`, `data_vencimento`, `estado`.",
    ["Model criado com todos os campos", "Estados: Pendente/Pago/Parcial/Em Atraso"],
    ["05-modelo-de-dados.md §5.19"])

add("finance", M3, "P0", "M", "Model Pagamento + Admin", ["5.20"],
    "Registo individual de pagamento, associado opcionalmente a uma mensalidade (ou emolumento avulso).",
    "`Pagamento(mensalidade opcional, aluno, numero_recibo, valor, meio_pagamento, data_pagamento, funcionario)`.",
    ["Model criado", "`numero_recibo` sequencial por instituição"],
    ["05-modelo-de-dados.md §5.20"])

add("finance", M3, "P0", "M", "Serviço gerar_plano_mensalidades() automático ao matricular", ["RF-FIN-02"],
    "Gerar automaticamente o plano de mensalidades do ano lectivo assim que a matrícula é confirmada.",
    "Signal `post_save` de `Matricula` (activa) dispara criação de uma `Mensalidade` por mês do calendário lectivo, com valores da `TabelaPrecos` aplicável.",
    ["Plano gerado automaticamente e correctamente distribuído pelos meses do ano lectivo", "Nenhuma duplicação em caso de re-execução (idempotente)"],
    ["02-requisitos-funcionais.md RF-FIN-02"])

add("finance", M3, "P0", "M", "Serviço registar_pagamento() com juro por atraso configurável", ["RF-FIN-03"],
    "Registar pagamentos de mensalidades/emolumentos, aplicando juro de mora configurável quando em atraso.",
    "```python\ndef registar_pagamento(mensalidade, valor, meio, funcionario):\n    juro = calcular_juro(mensalidade) if mensalidade.esta_em_atraso() else 0\n    ...\n```",
    ["Juro calculado correctamente segundo parametrização da instituição", "Estado da mensalidade actualizado (Pago/Parcial)"],
    ["02-requisitos-funcionais.md RF-FIN-03"])

add("finance", M3, "P0", "S", "Geração de recibo sequencial em PDF", ["RF-FIN-04"],
    "Emitir recibo imprimível com numeração sequencial e dados fiscais da instituição.",
    "Template WeasyPrint reutilizando dados de `Pagamento` e `Instituicao` (NIF, morada).",
    ["Recibo gerado automaticamente após registo de pagamento", "Numeração sequencial nunca reutilizada"],
    ["02-requisitos-funcionais.md RF-FIN-04"])

add("finance", M3, "P0", "M", "Extracto financeiro do aluno (dívidas, pagamentos, saldo)", ["RF-FIN-05"],
    "Vista consolidada da situação financeira do aluno, acessível a funcionários autorizados e ao encarregado no portal.",
    "View agregando `Mensalidade` + `Pagamento` do aluno, com saldo calculado.",
    ["Extracto correcto e acessível a Financeiro/Admin e ao encarregado do próprio educando", "Saldo reflecte juros aplicados"],
    ["02-requisitos-funcionais.md RF-FIN-05"])

add("finance", M3, "P1", "S", "Bloqueio configurável de documentos por dívida em aberto", ["RF-FIN-06"],
    "Impedir emissão de certos documentos (certificado, declaração) quando há dívida, se a instituição activar esta política.",
    "Verificação no serviço de emissão de documentos (`reports`) contra `Instituicao.bloqueia_documentos_com_divida` e saldo do aluno.",
    ["Bloqueio activável/desactivável por instituição", "Mensagem clara ao utilizador sobre o motivo do bloqueio"],
    ["02-requisitos-funcionais.md RF-FIN-06"])

add("finance", M3, "P1", "M", "Relatórios financeiros agregados (receita, inadimplência, projeção)", ["RF-FIN-07"],
    "Relatórios de apoio à decisão financeira da Direção.",
    "Views/consultas agregadas por período/turma/curso com gráficos Chart.js (servidos localmente).",
    ["Relatório de receita por período", "Mapa de inadimplência por turma/curso", "Projeção simples de receita futura"],
    ["02-requisitos-funcionais.md RF-FIN-07"])

add("finance", MF, "P2", "S", "Gestão de descontos e bolsas com aprovação", ["RF-FIN-08"],
    "Suportar descontos percentuais/fixos por aluno, com justificação e fluxo de aprovação.",
    "Model `Desconto(aluno, tipo, valor, justificacao, aprovado_por)` aplicado no cálculo do plano de mensalidades.",
    ["Desconto aplicável apenas após aprovação registada", "Reflectido correctamente no extracto financeiro"],
    ["02-requisitos-funcionais.md RF-FIN-08"])

# =====================================================================
# HR app
# =====================================================================

add("hr", M3, "P0", "S", "Model Seccao + Admin", ["5.22"],
    "Secções/departamentos funcionais da instituição (Secretaria, Direção, Financeiro, Pedagógico, RH, Biblioteca, TI, Apoio).",
    "`Seccao(nome, responsavel)` com fixture inicial das secções padrão.",
    ["Model criado", "Fixture com as secções padrão carregada na instalação"],
    ["05-modelo-de-dados.md §5.22"])

add("hr", M3, "P0", "S", "Model Cargo + Admin", ["5.22"],
    "Cargos/categorias profissionais dos funcionários.",
    "`Cargo(designacao)` com exemplos: Professor, Secretário(a), Tesoureiro(a), Director Pedagógico.",
    ["Model criado", "CRUD acessível a RH/Admin"],
    ["05-modelo-de-dados.md §5.22"])

add("hr", M3, "P0", "L", "Model Funcionario completo + Admin", ["RF-RH-01", "5.21"],
    "Registo de funcionários com dados pessoais, secção, cargo e ligação a conta de utilizador.",
    "Campos completos de 05-modelo-de-dados.md §5.21, incluindo `estado` (Activo/Inactivo/Licença/Rescisão).",
    ["Model criado com todos os campos", "Ligação 1-1 a `Utilizador`"],
    ["05-modelo-de-dados.md §5.21"])

add("hr", M3, "P1", "S", "Model Contrato + Admin", ["RF-RH-03", "5.23"],
    "Registo de vínculo contratual do funcionário, sem substituir um sistema de folha de pagamento.",
    "`Contrato(funcionario, tipo_vinculo, data_inicio, data_fim)`, tipos coerentes com a Lei Geral do Trabalho (Lei 12/23).",
    ["Model criado", "Tipos de vínculo alinhados com docs/legislacao/README.md (Lei 12/23)"],
    ["02-requisitos-funcionais.md RF-RH-03", "docs/legislacao/README.md"])

add("hr", M3, "P1", "M", "Fluxo de cadastro de funcionário por secção com herança automática de instituição", ["RF-RH-05"],
    "Cada secção gere os seus próprios funcionários, herdando automaticamente a instituição de quem cadastra (ver serviço criar_utilizador).",
    "Formulário de novo funcionário sem campo de instituição, reaproveitando `criar_utilizador()` de `accounts`.",
    ["Secretaria/RH/Financeiro/Pedagógico conseguem cadastrar os seus próprios funcionários", "Instituição sempre herdada automaticamente, nunca seleccionada"],
    ["02-requisitos-funcionais.md RF-RH-05", "04-arquitetura-tecnica.md §4.4.1"])

add("hr", M3, "P0", "M", "Associação Docente-Disciplina-Turma via Horário com controlo de carga horária", ["RF-RH-02"],
    "Garantir consistência entre a atribuição de docentes a turmas/disciplinas e o horário, controlando a carga horária total.",
    "Validação no `Horario` somando horas semanais por docente e alertando excesso face a um limite configurável.",
    ["Carga horária do docente calculada e visível a RH/Direção", "Alerta ao ultrapassar limite configurado"],
    ["02-requisitos-funcionais.md RF-RH-02"])

add("hr", M3, "P0", "S", "Gestão de estado do funcionário com reflexo automático no acesso ao sistema", ["RF-RH-04"],
    "Alterar o estado do funcionário (ex. Rescisão) deve desactivar automaticamente o acesso à conta ligada.",
    "Signal em `Funcionario.save()` que desactiva `Utilizador.is_active` quando `estado` muda para Inactivo/Rescisão.",
    ["Conta desactivada automaticamente ao mudar estado", "Reactivação possível apenas por acção administrativa explícita"],
    ["02-requisitos-funcionais.md RF-RH-04"])

# =====================================================================
# COMMUNICATIONS app
# =====================================================================

add("communications", M4, "P1", "M", "Model Aviso + Admin", ["5.25"],
    "Comunicados/notícias dirigidos a público geral, alunos, encarregados ou turma específica.",
    "`Aviso(titulo, corpo, publico_alvo, data_publicacao, visivel_no_portal_publico)`.",
    ["Model criado", "Suporta os 4 públicos-alvo definidos"],
    ["05-modelo-de-dados.md §5.25"])

add("communications", M4, "P1", "L", "Model Notificacao + fila multi-canal (SMS/Email/Portal)", ["5.25", "RF-ENC-04"],
    "Fila de notificações tolerante a falhas de conectividade, com estado e tentativas.",
    "`Notificacao(destinatario, canal, estado, tentativas, payload)`; worker Django-Q que processa a fila quando há rede.",
    ["Fila persiste notificações mesmo sem conectividade", "Reenvio automático com backoff em caso de falha"],
    ["02-requisitos-funcionais.md RF-ENC-04", "05-modelo-de-dados.md §5.25"])

add("communications", M4, "P1", "M", "Serviço de publicação de avisos por público-alvo", ["RF-PUB-02", "6.10"],
    "Publicar avisos visíveis conforme o público-alvo seleccionado, incluindo opção de visibilidade no portal público.",
    "View de criação de Aviso com selector de público-alvo e pré-visualização de quem o verá.",
    ["Aviso visível apenas ao público-alvo correcto", "Opção de visibilidade pública funcional"],
    ["02-requisitos-funcionais.md RF-PUB-02"])

add("communications", M5, "P1", "L", "Worker de envio de notificações (SMS/email/portal) tolerante a falhas", ["RF-ENC-04"],
    "Processar a fila de notificações pendentes assim que há conectividade, sem bloquear a operação local.",
    "Tarefa periódica Django-Q que tenta enviar notificações pendentes, marcando sucesso/falha e re-enfileirando com backoff.",
    ["Notificações pendentes enviadas automaticamente quando há rede", "Falhas não bloqueiam a operação local nem perdem a notificação"],
    ["02-requisitos-funcionais.md RF-ENC-04", "04-arquitetura-tecnica.md §4.7"])

add("communications", M5, "P2", "M", "Integração com gateway SMS (Unitel/Movicel/Africell)", ["4.8"],
    "Envio efectivo de SMS através de um agregador, como canal degradado sem dependência de smartphone/app.",
    "Adapter de gateway SMS plugável (interface comum), configurável por variável de ambiente; ausência de configuração não bloqueia o sistema.",
    ["Envio de SMS funcional quando configurado", "Sistema opera normalmente sem esta integração configurada"],
    ["04-arquitetura-tecnica.md §4.8"])

add("communications", M4, "P2", "S", "Painel de histórico de comunicações enviadas", ["6.10"],
    "Consulta de avisos e notificações já enviados, para auditoria e suporte.",
    "Listagem filtrável por canal/data/destinatário/estado.",
    ["Histórico consultável por Admin/Comunicação"],
    ["06-modulos-e-funcionalidades.md §6.10"])

# =====================================================================
# REPORTS app
# =====================================================================

add("reports", M2, "P0", "M", "Template base de documentos oficiais (numeração/série única, emissor)", ["RF-REL-06"],
    "Base reutilizável para todos os documentos oficiais gerados pelo sistema.",
    "Template HTML base com cabeçalho institucional, rodapé com numeração/série, data/hora e funcionário emissor; contador sequencial por tipo de documento e instituição.",
    ["Numeração nunca reutilizada, mesmo em caso de falha a meio da emissão", "Toda emissão regista entrada de auditoria"],
    ["02-requisitos-funcionais.md RF-REL-06"])

add("reports", M2, "P0", "M", "Geração de Declaração (matrícula/frequência/conclusão)", ["RF-REL-01"],
    "Documentos de declaração com modelo configurável por instituição.",
    "3 templates (matrícula/frequência/conclusão) parametrizáveis com textos legais próprios por instituição.",
    ["3 tipos de declaração geráveis em PDF", "Cabeçalho/textos legais configuráveis por instituição"],
    ["02-requisitos-funcionais.md RF-REL-01"])

add("reports", M3, "P0", "M", "Geração de Certificado de conclusão de curso/classe", ["RF-REL-02"],
    "Certificado emitido apenas quando a situação final do aluno é 'concluído/aprovado'.",
    "Template de certificado validando `calcular_situacao_final()` antes de permitir emissão.",
    ["Certificado só emitido para alunos com situação final compatível", "PDF gerado com numeração/série única"],
    ["02-requisitos-funcionais.md RF-REL-02"])

add("reports", M2, "P0", "M", "Geração de Pauta oficial (turma/disciplina/período/ano)", ["RF-REL-03"],
    "Documento oficial consolidando classificações por turma.",
    "Reaproveita a view de Pauta de `grading`, exportando em PDF via WeasyPrint.",
    ["Pauta oficial exportável em PDF, com todos os alunos da turma"],
    ["02-requisitos-funcionais.md RF-REL-03"])

add("reports", M2, "P0", "S", "Geração de Boletim de notas por aluno/período", ["RF-REL-04"],
    "Extracto individual de notas do aluno.",
    "Reaproveita a view de Boletim de `grading`, exportando em PDF.",
    ["Boletim exportável em PDF por aluno e período"],
    ["02-requisitos-funcionais.md RF-REL-04"])

add("reports", M3, "P1", "M", "Relatórios estatísticos (taxa de aprovação, abandono, inadimplência)", ["RF-REL-05"],
    "Relatórios de apoio à decisão da Direção, combinando dados de grading/finance/enrollment.",
    "Consultas agregadas com visualização via Chart.js, exportáveis também em PDF/CSV.",
    ["3 relatórios estatísticos disponíveis (aprovação, abandono, inadimplência)", "Exportação em PDF e CSV"],
    ["02-requisitos-funcionais.md RF-REL-05"])

add("reports", M2, "P1", "S", "Configuração de modelo de documento por instituição", ["RF-REL-01"],
    "Permitir à instituição personalizar cabeçalho e textos legais dos documentos oficiais.",
    "Ecrã de configuração em `admin_panel` associado aos templates de `reports`.",
    ["Cabeçalho/logótipo/textos legais editáveis por instituição", "Alterações reflectidas em todos os documentos subsequentes"],
    ["02-requisitos-funcionais.md RF-REL-01"])

# =====================================================================
# PUBLIC SITE app
# =====================================================================

add("public-site", M1, "P0", "M", "Página institucional (apresentação, cursos, contactos, localização)", ["RF-PUB-01"],
    "Sítio público sem autenticação, acessível tanto no Nó Central como no Nó Local (LAN da escola).",
    "Templates públicos usando os dados de `Instituicao` e `Curso`; acessível em ambos os nós conforme 06-modulos-e-funcionalidades.md §6.3.",
    ["Página acessível sem login", "Reflecte dados reais da instituição (cursos, contactos, morada)"],
    ["02-requisitos-funcionais.md RF-PUB-01", "06-modulos-e-funcionalidades.md §6.3"])

add("public-site", M1, "P0", "S", "Mural de comunicados/notícias público", ["RF-PUB-02"],
    "Publicar avisos institucionais visíveis sem autenticação (prazos de matrícula, eventos, calendário).",
    "Lista de `Aviso` filtrada por `visivel_no_portal_publico=True`.",
    ["Mural acessível sem login", "Conteúdo consistente com o publicado internamente"],
    ["02-requisitos-funcionais.md RF-PUB-02"])

add("public-site", M1, "P1", "S", "Formulário de pré-candidatura/contacto para o público em geral", ["RF-PUB-03"],
    "Captar interesse de candidatos antes da inscrição efectiva.",
    "Formulário que cria um `Candidato` (enrollment) directamente a partir do portal público.",
    ["Submissão cria Candidato correctamente", "Validação básica de campos obrigatórios"],
    ["02-requisitos-funcionais.md RF-PUB-03"])

add("public-site", M4, "P2", "M", "Consulta pública opcional de resultados com dados minimizados", ["RF-PUB-04"],
    "Permitir à instituição publicar resultados de exames por número de aluno (nunca por nome completo), se assim optar.",
    "View pública com busca por número de aluno, mostrando apenas classificação, nunca dados pessoais.",
    ["Busca funcional apenas por número de aluno", "Nenhum dado pessoal exposto (nome completo, documento, etc.)", "Funcionalidade activável/desactivável por instituição"],
    ["02-requisitos-funcionais.md RF-PUB-04"])

add("public-site", M1, "P1", "S", "Calendário escolar público (ano letivo, períodos, feriados)", ["6.3"],
    "Disponibilizar publicamente o calendário do ano lectivo corrente.",
    "View pública derivada de `AnoLectivo`/`PeriodoLectivo`/`DiaNaoLectivo`.",
    ["Calendário reflecte o ano lectivo corrente e os feriados configurados"],
    ["06-modulos-e-funcionalidades.md §6.3"])

# =====================================================================
# STUDENT PORTAL app
# =====================================================================

add("student-portal", M4, "P0", "L", "Dashboard do aluno: matrícula, horário, notas, frequência", ["RF-ALU-01"],
    "Painel principal do portal do aluno com toda a informação académica relevante.",
    "Views agregando `Matricula`, `Horario` (via turma), `Nota`, `Presenca` do aluno autenticado (ou do encarregado agindo em seu nome).",
    ["Todas as secções (matrícula/horário/notas/frequência) funcionais e correctamente restritas ao próprio aluno"],
    ["02-requisitos-funcionais.md RF-ALU-01"])

add("student-portal", M4, "P1", "S", "Extracto financeiro do aluno no portal", ["RF-ALU-02"],
    "Consulta de mensalidades pagas/pendentes pelo próprio aluno.",
    "Reaproveita a view de extracto financeiro de `finance`, com âmbito restrito ao próprio aluno.",
    ["Extracto visível apenas ao próprio aluno"],
    ["02-requisitos-funcionais.md RF-ALU-02"])

add("student-portal", M4, "P1", "S", "Recepção de avisos dirigidos à turma/curso/instituição", ["RF-ALU-03"],
    "Mostrar ao aluno os avisos relevantes ao seu contexto.",
    "Filtragem de `Aviso` por público-alvo compatível com a turma/curso do aluno.",
    ["Aluno vê apenas avisos dirigidos a si/turma/curso/instituição"],
    ["02-requisitos-funcionais.md RF-ALU-03"])

add("student-portal", M5, "P1", "L", "PWA: cache offline de leitura + indicação de dados desatualizados", ["RF-ALU-04", "8.8"],
    "Permitir consulta offline dos últimos dados sincronizados, com indicação clara de possível desactualização.",
    "Service Worker (stale-while-revalidate) + Web App Manifest conforme 08-offline-first-e-sincronizacao.md §8.8.",
    ["Portal funciona offline com últimos dados em cache", "Indicação visual clara de 'dados de [data/hora]' quando offline"],
    ["02-requisitos-funcionais.md RF-ALU-04", "08-offline-first-e-sincronizacao.md §8.8"])

# =====================================================================
# GUARDIAN PORTAL app
# =====================================================================

add("guardian-portal", M4, "P0", "L", "Painel consolidado multi-educando", ["RF-ENC-01"],
    "Vista consolidada de notas, frequência e situação financeira de todos os educandos do encarregado.",
    "Dashboard que itera sobre todos os `EncarregadoAluno` do utilizador autenticado.",
    ["Todos os educandos do encarregado visíveis num único login", "Selector de educando quando há mais de um"],
    ["02-requisitos-funcionais.md RF-ENC-01"])

add("guardian-portal", M4, "P1", "M", "Fluxo de pedidos ao secretariado (justificação de falta, declaração)", ["RF-ENC-02"],
    "Permitir ao encarregado submeter pedidos através do portal, processados manualmente pela Secretaria.",
    "Model `PedidoEncarregado(tipo, educando, descricao, estado)` com fila visível à Secretaria.",
    ["Pedido submetido pelo encarregado aparece na fila da Secretaria", "Estado do pedido visível ao encarregado"],
    ["02-requisitos-funcionais.md RF-ENC-02"])

add("guardian-portal", M4, "P0", "S", "Atualização de dados de contacto próprios do encarregado", ["RF-ENC-03"],
    "Permitir ao encarregado manter os seus próprios dados de contacto actualizados.",
    "Formulário de edição restrito aos campos de contacto do próprio `EncarregadoEducacao`.",
    ["Encarregado só altera os seus próprios dados, nunca os do aluno"],
    ["02-requisitos-funcionais.md RF-ENC-03"])

add("guardian-portal", M4, "P1", "S", "Recepção de notificações multi-canal no portal", ["RF-ENC-04"],
    "Mostrar no portal o histórico de notificações recebidas pelo encarregado.",
    "Lista de `Notificacao` filtrada pelo destinatário autenticado.",
    ["Notificações visíveis no portal independentemente do canal de envio original"],
    ["02-requisitos-funcionais.md RF-ENC-04"])

# =====================================================================
# ADMIN PANEL app
# =====================================================================

add("admin-panel", M1, "P0", "L", "Gestão de utilizadores/perfis/permissões granulares", ["RF-ADM-01"],
    "Área administrativa para gerir contas, perfis e permissões por módulo.",
    "CRUD de `Utilizador` com atribuição de `Perfil`/Grupos e permissões granulares por módulo.",
    ["Administrador consegue gerir utilizadores/perfis sem usar o Django Admin cru", "Permissões reflectem a matriz de 07-perfis-permissoes-e-fluxos.md §7.2"],
    ["02-requisitos-funcionais.md RF-ADM-01"])

add("admin-panel", M1, "P0", "M", "Configuração de parâmetros globais da instituição", ["RF-ADM-02"],
    "Ecrã único para configurar ano lectivo, fórmulas de média, tabelas de preços, feriados.",
    "Painel de configuração agregando as telas já criadas em `core`/`finance`.",
    ["Todos os parâmetros de §2.1 acessíveis a partir de um único painel"],
    ["02-requisitos-funcionais.md RF-ADM-02"])

add("admin-panel", M5, "P0", "L", "Painel de auditoria", ["RF-ADM-03", "9.4"],
    "Consulta de quem alterou o quê e quando, para notas, matrículas, pagamentos e utilizadores.",
    "View de pesquisa sobre `audit.RegistoAuditoria` filtrável por entidade/utilizador/período.",
    ["Pesquisa funcional por entidade, utilizador e período", "Registos de auditoria imutáveis (sem edição/eliminação via UI)"],
    ["02-requisitos-funcionais.md RF-ADM-03", "09-seguranca-e-privacidade.md §9.4"])

add("admin-panel", M5, "P0", "L", "Painel de estado de sincronização", ["RF-ADM-04", "8.11"],
    "Painel central de visibilidade sobre o estado da sincronização offline/online.",
    "Ver especificação completa em 08-offline-first-e-sincronizacao.md §8.11: último sync, pendências, conflitos, histórico, botão 'Sincronizar agora', botão 'Gerar pacote de contingência'.",
    ["Todos os elementos de §8.11 presentes e funcionais", "Atalho directo da lista de conflitos para o ecrã de resolução"],
    ["08-offline-first-e-sincronizacao.md §8.11"])

add("admin-panel", M3, "P0", "M", "Exportação de dados (CSV/JSON/PDF)", ["RF-ADM-05"],
    "Permitir backup manual e exportações normativas em formatos abertos.",
    "Views de exportação por entidade (alunos, matrículas, notas, financeiro) em CSV/JSON, e relatórios em PDF.",
    ["Exportação funcional nos 3 formatos para as entidades principais"],
    ["02-requisitos-funcionais.md RF-ADM-05"])

add("admin-panel", M6, "P1", "L", "Painel de Super Administrador multi-instituição", ["RF-ADM-06"],
    "Gestão de múltiplas instituições a partir do Nó Central por um Super Administrador.",
    "Painel com selector explícito de instituição para visualização (único caso de selecção manual, conforme 4.4.4), métricas agregadas por instituição.",
    ["Super Administrador consegue navegar entre instituições sem ambiguidade de tenant", "Métricas agregadas (alunos, sync, etc.) por instituição"],
    ["02-requisitos-funcionais.md RF-ADM-06", "04-arquitetura-tecnica.md §4.4.4"])

add("admin-panel", M1, "P1", "M", "Painel 'Tarefas Atuais' por perfil (dashboard)", ["6.15"],
    "Painel personalizado por perfil com pendências accionáveis, reinterpretando o menu original.",
    "Dashboard com widgets específicos por perfil (Secretaria: candidaturas por processar; Docente: pautas por lançar; Financeiro: mensalidades vencidas; etc.).",
    ["Cada perfil vê pendências relevantes ao seu papel", "Widgets accionáveis (levam directamente à acção pendente)"],
    ["06-modulos-e-funcionalidades.md §6.15"])

# =====================================================================
# SYNC app — crítico
# =====================================================================

add("sync", M0, "P0", "M", "Model RegistoAlteracao (outbox/changelog)", ["5.26", "8.3"],
    "Tabela central do padrão outbox: uma linha por cada alteração de negócio a sincronizar.",
    "`RegistoAlteracao(entidade, entidade_id, operacao, payload_json, origin_node_id, criado_em, sincronizado_em)`.",
    ["Model criado", "Índice por `sincronizado_em` (NULL = pendente) para consulta eficiente"],
    ["05-modelo-de-dados.md §5.26"])

add("sync", M0, "P0", "S", "Model SessaoSincronizacao", ["5.26", "8.3"],
    "Regista cada tentativa de sincronização, permitindo retomar e auditar.",
    "`SessaoSincronizacao(node_id, iniciada_em, concluida_em, estado, registos_enviados, registos_recebidos, erros)`.",
    ["Model criado", "Usado pelo painel de sincronização (RF-ADM-04)"],
    ["05-modelo-de-dados.md §5.26"])

add("sync", M5, "P0", "M", "Model Conflito", ["5.26", "8.6"],
    "Fila de conflitos detectados durante a sincronização, com as duas versões e estado de resolução.",
    "`Conflito(entidade, entidade_id, versao_local_json, versao_remota_json, estado, resolvido_por)`.",
    ["Model criado", "Suporta os 3 estados: Pendente/ResolvidoAutomaticamente/ResolvidoManualmente"],
    ["05-modelo-de-dados.md §5.26"])

add("sync", M0, "P0", "S", "Model Node (identidade de cada nó, chave pública)", ["5.26", "8.5"],
    "Identidade única de cada Nó Local/Central usada na autenticação mútua da sincronização.",
    "`Node(id, tipo, instituicao_id, ultimo_sync_em, chave_publica)`.",
    ["Model criado", "Chave gerada na instalação (setup wizard) e nunca reutilizada entre nós"],
    ["05-modelo-de-dados.md §5.26"])

add("sync", M0, "P0", "L", "Signal genérico post_save/post_delete → grava RegistoAlteracao na mesma transação", ["8.4"],
    "Núcleo do padrão outbox: garantir que nenhuma alteração de negócio escapa ao registo de sincronização.",
    "Signal registado no mixin `SyncedModel` (não por app individual), serializando o estado pós-alteração e incrementando `version`.",
    ["Toda alteração a um model `SyncedModel` gera exactamente um `RegistoAlteracao`", "Gravação atómica (mesma transacção) comprovada por teste com rollback forçado"],
    ["08-offline-first-e-sincronizacao.md §8.4"])

add("sync", M5, "P0", "L", "Endpoint API POST /api/sync/push (DRF) com validação de assinatura/token do Node", ["8.5"],
    "Endpoint que recebe lotes de alterações de um Nó Local, valida autenticidade e aplica segundo a lógica de versão/conflito.",
    "DRF APIView com autenticação customizada por chave de Node; lotes paginados (~200 registos), resposta com ACK idempotente.",
    ["Endpoint rejeita nós não registados", "Aplicação idempotente (reenvio do mesmo lote não duplica efeitos)", "Testado com lotes de diferentes tamanhos"],
    ["08-offline-first-e-sincronizacao.md §8.5"])

add("sync", M5, "P0", "L", "Endpoint API GET /api/sync/pull com last_sync_token/cursor", ["8.5"],
    "Endpoint que devolve ao Nó Local as alterações originadas noutros nós desde a última sincronização.",
    "Cursor baseado em `criado_em`/sequência do changelog; resposta comprimida (gzip).",
    ["Apenas deltas devolvidos (nunca dataset completo)", "Cursor avança correctamente entre chamadas sucessivas"],
    ["08-offline-first-e-sincronizacao.md §8.5", "03-requisitos-nao-funcionais.md RNF-PERF-03"])

add("sync", M5, "P0", "L", "Lógica de aplicação de changelog recebido (idempotente por UUID/version)", ["8.5"],
    "Aplicar localmente as alterações recebidas do outro lado, respeitando a mesma lógica de versão/conflito em ambas as direcções.",
    "Função partilhada `aplicar_registo_alteracao(registo)` usada tanto pelo push (lado central) como pelo pull (lado local) e pela importação sneakernet.",
    ["Mesma função usada nos 3 caminhos (push/pull/sneakernet) — sem duplicação de lógica", "Idempotência comprovada por teste (aplicar duas vezes = no-op)"],
    ["08-offline-first-e-sincronizacao.md §8.5", "13-testes-e-qualidade.md §13.3.2"])

add("sync", M5, "P1", "M", "Worker periódico de sincronização no Nó Local (Django-Q, detecção de conectividade)", ["8.5"],
    "Tentar sincronizar automaticamente sempre que há conectividade, sem intervenção manual.",
    "Tarefa Django-Q agendada (ex. a cada 5 min); ping leve ao endpoint central para detectar conectividade antes de tentar o lote completo.",
    ["Sincronização automática sem intervenção manual", "Nenhuma tentativa desnecessária quando claramente offline (detecção rápida)"],
    ["08-offline-first-e-sincronizacao.md §8.5", "02-requisitos-funcionais.md RF-SYNC-02"])

add("sync", M5, "P1", "S", "Compressão gzip do payload de sincronização", ["RNF-PERF-03"],
    "Minimizar consumo de dados móveis durante a sincronização.",
    "Middleware/decorator DRF que comprime request/response dos endpoints de sync.",
    ["Payloads de sync comprimidos", "Redução mensurável de bytes transmitidos em teste de referência"],
    ["03-requisitos-nao-funcionais.md RNF-PERF-03"])

add("sync", M5, "P0", "L", "Classificação de conflitos: sem conflito / merge automático / LWW / crítico", ["8.6.1"],
    "Implementar a árvore de decisão de classificação de conflitos conforme documentado.",
    "Função `classificar_conflito(local, remoto)` que determina a estratégia aplicável segundo a tabela de 08-offline-first-e-sincronizacao.md §8.6.1.",
    ["4 categorias implementadas e testadas com casos determinísticos", "Notas/Pagamentos/Matrículas sempre classificados como críticos"],
    ["08-offline-first-e-sincronizacao.md §8.6.1"])

add("sync", M5, "P0", "M", "Merge automático campo-a-campo para conflitos não críticos", ["8.6.1"],
    "Resolver automaticamente conflitos onde campos diferentes foram alterados sem sobreposição.",
    "Função de merge que compara campo a campo entre versão local/remota e combina quando não há sobreposição.",
    ["Merge automático correcto para o caso de exemplo (telefone vs endereço)", "Nunca aplicado a entidades críticas"],
    ["08-offline-first-e-sincronizacao.md §8.6.1"])

add("sync", M5, "P0", "M", "Last-Write-Wins com registo do valor descartado em auditoria", ["8.6.1"],
    "Para conflitos de concorrência simples em entidades não críticas, aplicar LWW preservando o valor descartado.",
    "Ao resolver por LWW, gravar o valor não aplicado em `audit.RegistoAuditoria` antes de descartar.",
    ["Valor descartado sempre preservado em auditoria, nunca perdido silenciosamente"],
    ["08-offline-first-e-sincronizacao.md §8.6.1"])

add("sync", M5, "P0", "L", "Fila de resolução manual para conflitos críticos (Nota/Pagamento/Matrícula)", ["8.6.2"],
    "Bloquear aplicação automática para entidades críticas, colocando-as em fila de decisão humana.",
    "Ao detectar conflito crítico, criar `Conflito(estado=Pendente)` em vez de aplicar qualquer versão automaticamente.",
    ["Nenhum conflito crítico aplicado automaticamente, comprovado por teste", "Conflito aparece imediatamente no painel de sincronização"],
    ["08-offline-first-e-sincronizacao.md §8.6.2"])

add("sync", M5, "P0", "L", "Interface de resolução de conflitos lado-a-lado", ["8.6.3"],
    "Ecrã dedicado para o Administrador decidir entre versão local, remota ou edição manual.",
    "View com diff destacado entre as duas versões, contexto (aluno/disciplina/data/utilizador de origem) e as 3 acções descritas em §8.6.3.",
    ["As 3 acções (Aceitar Local/Aceitar Remota/Editar Manualmente) funcionais", "Resolução regista auditoria de quem resolveu e como"],
    ["08-offline-first-e-sincronizacao.md §8.6.3"])

add("sync", M5, "P1", "L", "Geração de pacote de contingência cifrado .fsxsync (sneakernet)", ["8.7"],
    "Permitir sincronização por transporte físico quando não há qualquer via de rede.",
    "Exportação do changelog pendente, assinado e cifrado com a chave do Node de destino, num único ficheiro `.fsxsync`.",
    ["Pacote gerado contém exactamente o changelog pendente", "Ficheiro cifrado — ilegível sem a chave do Node de destino"],
    ["08-offline-first-e-sincronizacao.md §8.7"])

add("sync", M5, "P1", "M", "Importação manual de pacote .fsxsync no Nó Central", ["8.7"],
    "Aplicar um pacote de contingência reutilizando exactamente a mesma lógica de validação/conflito do fluxo automático.",
    "Ecrã de importação que chama a mesma função `aplicar_registo_alteracao()` usada no push/pull.",
    ["Importação aplica o pacote com a mesma lógica de conflito do fluxo automático", "Pacote inverso (Central→Local) também suportado"],
    ["08-offline-first-e-sincronizacao.md §8.7"])

add("sync", M4, "P1", "L", "PWA service worker stale-while-revalidate para portais externos", ["8.8"],
    "Cache offline de leitura para os portais de Aluno/Encarregado.",
    "Service Worker com estratégia stale-while-revalidate para notas/horário/avisos.",
    ["Conteúdo de leitura disponível offline com o último dado sincronizado"],
    ["08-offline-first-e-sincronizacao.md §8.8"])

add("sync", M4, "P1", "M", "Background Sync API para escritas do portal (justificação de falta, contacto)", ["8.8"],
    "Permitir que as poucas escritas destes portais sejam enfileiradas offline e reenviadas automaticamente.",
    "Fila em IndexedDB no browser + Background Sync API para reenvio automático quando a rede volta.",
    ["Pedido submetido offline é reenviado automaticamente ao reconectar", "Nenhuma perda de submissão em teste de desconexão forçada"],
    ["08-offline-first-e-sincronizacao.md §8.8"])

add("sync", M5, "P0", "L", "Painel de Estado de Sincronização completo", ["RF-ADM-04", "8.11"],
    "Consolidar todos os elementos do painel descrito em §8.11 (parte final de implementação, após os módulos individuais).",
    "Último sync, pendências, conflitos, histórico de sessões, botão 'Sincronizar agora', botão 'Gerar pacote de contingência'.",
    ["Todos os 6 elementos de §8.11 presentes e funcionais em conjunto"],
    ["08-offline-first-e-sincronizacao.md §8.11"])

# =====================================================================
# SECURITY / AUDIT
# =====================================================================

add("audit", M1, "P0", "M", "Model RegistoAuditoria + signals em entidades críticas", ["5.27", "RNF-AUD-01"],
    "Registo transversal de auditoria usado por Nota, Matrícula, Pagamento, Utilizador, Permissão.",
    "`RegistoAuditoria(utilizador, acao, entidade, entidade_id, valores_antes_json, valores_depois_json, ip_origem, timestamp)`; signals conectados às 5 entidades críticas.",
    ["Registo criado para toda alteração/eliminação nas 5 entidades críticas", "Registos imutáveis (sem update/delete via aplicação)"],
    ["05-modelo-de-dados.md §5.27", "03-requisitos-nao-funcionais.md RNF-AUD-01"])

add("security", M2, "P0", "M", "Cifra de campo para dados sensíveis (BI, contactos de encarregados)", ["RNF-SEC-06", "9.3"],
    "Proteger em repouso os campos mais sensíveis, mesmo na base de dados local.",
    "`django-cryptography` aplicado aos campos `numero_documento` e contactos directos de `EncarregadoEducacao`.",
    ["Campos cifrados em repouso na base local e central", "Leitura/escrita transparente para a aplicação (sem alterar lógica de negócio)"],
    ["03-requisitos-nao-funcionais.md RNF-SEC-06", "09-seguranca-e-privacidade.md §9.3"])

add("security", M0, "P0", "M", "Configuração TLS 1.2+ (Nginx, certificados, mTLS Nó-Nó)", ["RNF-SEC-01", "9.3"],
    "Garantir cifra em trânsito em toda a comunicação, incluindo entre Nó Local e Central.",
    "Nginx com certificado (auto-assinado na LAN da escola + certificado público no Nó Central); autenticação mútua adicional na sincronização.",
    ["TLS 1.2+ obrigatório em todos os endpoints", "Certificado raiz distribuído aos dispositivos da instituição quando auto-assinado"],
    ["03-requisitos-nao-funcionais.md RNF-SEC-01", "09-seguranca-e-privacidade.md §9.3"])

add("security", M1, "P0", "S", "Consentimento do encarregado no ato de inscrição (checkbox + timestamp)", ["9.1", "RNF-AUD-02"],
    "Cumprir o requisito de consentimento da Lei 22/11 para tratamento de dados de menores.",
    "Campo obrigatório no formulário de Inscrição, gravado com timestamp e associado ao encarregado que consentiu.",
    ["Inscrição bloqueada sem consentimento registado", "Timestamp e encarregado consentidor auditáveis"],
    ["09-seguranca-e-privacidade.md §9.1", "docs/legislacao/lei-22-11-protecao-dados-pessoais.pdf"])

add("security", M3, "P1", "M", "Ecrã de exportação de dados de um titular (direito de acesso/rectificação)", ["9.1"],
    "Suportar o direito de acesso e rectificação previsto na Lei 22/11.",
    "Ecrã em `admin_panel` que exporta todos os dados pessoais de um Aluno/Encarregado/Funcionário a pedido.",
    ["Exportação completa e legível dos dados pessoais de um titular", "Acesso restrito a perfis autorizados"],
    ["09-seguranca-e-privacidade.md §9.1"])

add("security", M4, "P1", "S", "Procedimento de resposta a incidentes + relatório de âmbito", ["9.5"],
    "Documentar e instrumentar a resposta a incidentes de segurança/privacidade.",
    "Runbook documentado + relatório automatizável de âmbito (que dados, quantos titulares, período) a partir dos logs de auditoria.",
    ["Runbook documentado e acessível à equipa técnica", "Relatório de âmbito gerável a partir da auditoria existente"],
    ["09-seguranca-e-privacidade.md §9.5"])

add("security", M0, "P0", "S", "Hardening de headers HTTP (django-csp, SECURE_* settings)", ["9.7"],
    "Aplicar boas práticas de segurança HTTP desde o início do projeto.",
    "`SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS`, `django-csp` configurado.",
    ["Cabeçalhos de segurança presentes em todas as respostas", "CSP configurado sem quebrar HTMX/Alpine.js"],
    ["09-seguranca-e-privacidade.md §9.7"])

add("security", M0, "P0", "XS", "pip-audit integrado no CI", ["9.7"],
    "Detectar vulnerabilidades conhecidas em dependências antes de qualquer merge.",
    "Passo `pip-audit` no workflow de CI (ver tarefa de pipeline CI).",
    ["Build falha se houver vulnerabilidade crítica conhecida sem excepção justificada"],
    ["09-seguranca-e-privacidade.md §9.7"])

# =====================================================================
# I18N
# =====================================================================

add("i18n", M1, "P0", "M", "Configuração LANGUAGES + catálogos locale/<code> (pt, umb, kmb, kon, cjk, kua)", ["RF-I18N-01", "10.4.1"],
    "Base técnica do multilinguismo: português obrigatório + 5 línguas nacionais como opção pessoal.",
    "`LANGUAGES` e `LOCALE_PATHS` conforme 10-stack-tecnologica-e-estrutura-projeto.md §10.4.1; estrutura de pastas `locale/<code>/LC_MESSAGES/`.",
    ["6 idiomas configurados (pt + 5 nacionais)", "Estrutura de catálogos criada mesmo antes da tradução completa"],
    ["10-stack-tecnologica-e-estrutura-projeto.md §10.4.1"])

add("i18n", M1, "P0", "M", "Middleware de idioma por preferência do utilizador (não Accept-Language)", ["10.4.1"],
    "Resolver o idioma da interface a partir de `idioma_preferido`, não do cabeçalho do navegador.",
    "Middleware fino que chama `translation.activate(request.user.idioma_preferido)` logo após autenticação.",
    ["Idioma da interface determinado sempre pela preferência gravada, nunca pelo browser", "Utilizador anónimo usa `pt` por omissão"],
    ["10-stack-tecnologica-e-estrutura-projeto.md §10.4.1"])

add("i18n", M1, "P1", "S", "Extração de strings (makemessages) e processo de tradução incremental", ["10.4.2"],
    "Preparar o fluxo humano de tradução, dado que não existem catálogos prontos para línguas angolanas.",
    "Comando `django-admin makemessages -l umb -l kmb -l kon -l cjk -l kua`; processo documentado de colaboração com falantes nativos/ILN.",
    ["Comando de extracção documentado e testado", "Processo de tradução incremental descrito para a equipa/colaboradores"],
    ["10-stack-tecnologica-e-estrutura-projeto.md §10.4.2"])

add("i18n", M1, "P1", "M", "Marcação de todos os templates fixos com {% trans %}/{% blocktrans %}",
    ["10.4.3"],
    "Garantir que todos os textos fixos da interface (menus, botões, mensagens) são traduzíveis.",
    "Revisão sistemática de templates base e de cada app, substituindo texto literal por tags de tradução.",
    ["Nenhum texto fixo de interface hardcoded sem tag de tradução nos ecrãs principais (login, matrícula, notas, financeiro)"],
    ["10-stack-tecnologica-e-estrutura-projeto.md §10.4.3"])

add("i18n", M1, "P0", "XS", "Garantir que documentos oficiais permanecem sempre em português", ["RF-I18N-03"],
    "Documentos oficiais nunca devem ser traduzidos, por validade legal/administrativa.",
    "Templates de `reports` fixam explicitamente `language='pt'` na geração de PDF, independentemente do idioma do utilizador solicitante.",
    ["Certificados/declarações/pautas/recibos sempre em português, mesmo para utilizador com outro idioma preferido"],
    ["02-requisitos-funcionais.md RF-I18N-03"])

# =====================================================================
# TESTING
# =====================================================================

add("testing", M0, "P0", "M", "Setup pytest-django + factories (factory_boy) por app", ["13.1"],
    "Base de testes reutilizável para todas as apps.",
    "`conftest.py` com fixtures comuns (instituição de teste, utilizador de cada perfil); `factories.py` por app usando `factory_boy`.",
    ["Factories disponíveis para as entidades principais de cada app", "Fixtures comuns reutilizadas em todos os testes"],
    ["13-testes-e-qualidade.md §13.1"])

add("testing", M1, "P0", "M", "Testes unitários dos services críticos (matricular_aluno, lancar_nota, fechar_pauta, registar_pagamento)", ["13.1", "13.2"],
    "Cobertura mínima de 70% no núcleo de negócio.",
    "Testes cobrindo caminho feliz e caminhos de erro (turma lotada, nota fora de escala, pauta fechada, mensalidade inexistente).",
    ["Cobertura ≥ 70% nos 4 services", "Casos de erro testados, não só o caminho feliz"],
    ["13-testes-e-qualidade.md §13.2"])

add("testing", M2, "P1", "M", "Testes de integração: fluxo completo Inscrição→Matrícula", ["13.1"],
    "Validar o fluxo de ponta a ponta reproduzindo o exemplo do documento original.",
    "Teste usando `Client` do Django simulando o fluxo completo de Inscrição seguido de Matrícula.",
    ["Fluxo completo testado com dados equivalentes ao exemplo original (aluna Yolene Hangalo)"],
    ["13-testes-e-qualidade.md §13.1"])

add("testing", M2, "P1", "M", "Testes de integração: Lançamento→Fecho de Pauta→Boletim", ["13.1"],
    "Validar o fluxo pedagógico completo de um período lectivo.",
    "Teste cobrindo lançamento de notas, submissão, homologação, bloqueio de edição e geração de boletim.",
    ["Fluxo completo testado, incluindo tentativa de edição após fecho (deve falhar)"],
    ["13-testes-e-qualidade.md §13.1"])

add("testing", M3, "P1", "M", "Testes de integração: Matrícula→Plano de Mensalidades→Pagamento→Recibo", ["13.1"],
    "Validar o fluxo financeiro completo desencadeado pela matrícula.",
    "Teste cobrindo geração automática do plano, registo de pagamento parcial e total, emissão de recibo.",
    ["Fluxo completo testado incluindo cálculo de juro por atraso"],
    ["13-testes-e-qualidade.md §13.1"])

add("testing", M5, "P0", "L", "Suite de testes de sincronização: partição de rede simulada", ["13.3"],
    "Validar retomada correcta de sincronização após corte de rede a meio do processo.",
    "Dois containers Django em rede Docker isolada, cortada a meio de uma sincronização via `docker network disconnect`.",
    ["Ambos os nós permanecem consistentes após reconexão", "Retomada correcta sem duplicação"],
    ["13-testes-e-qualidade.md §13.3.1"])

add("testing", M5, "P0", "M", "Suite de testes de sincronização: idempotência", ["13.3"],
    "Garantir que reenviar o mesmo lote de sincronização não duplica efeitos.",
    "Reenvio do mesmo `RegistoAlteracao` duas vezes, validando resultado idêntico ao de uma única aplicação.",
    ["Segunda aplicação do mesmo lote é comprovadamente no-op"],
    ["13-testes-e-qualidade.md §13.3.2"])

add("testing", M5, "P0", "M", "Suite de testes de sincronização: conflito não-crítico / merge automático", ["13.3"],
    "Validar o merge automático campo-a-campo.",
    "Cenário com dois campos diferentes alterados offline em nós distintos para o mesmo registo não crítico.",
    ["Merge automático produz o resultado esperado (ambos os campos aplicados)"],
    ["13-testes-e-qualidade.md §13.3.3"])

add("testing", M5, "P0", "M", "Suite de testes de sincronização: conflito crítico / fila manual", ["13.3"],
    "Garantir que Notas/Pagamentos/Matrículas em conflito nunca são resolvidos automaticamente.",
    "Cenário com a mesma Nota alterada de forma divergente em dois nós; validar entrada em `Conflito` e ausência de aplicação automática.",
    ["Conflito sempre detectado e nunca resolvido automaticamente para estas 3 entidades"],
    ["13-testes-e-qualidade.md §13.3.4"])

add("testing", M5, "P1", "M", "Suite de testes de sincronização: sneakernet", ["13.3"],
    "Validar que o pacote de contingência produz o mesmo resultado que o fluxo automático.",
    "Gerar pacote `.fsxsync`, importar noutro nó, comparar resultado com o fluxo de sincronização normal para o mesmo changelog.",
    ["Resultado idêntico entre importação sneakernet e sincronização automática"],
    ["13-testes-e-qualidade.md §13.3.5"])

add("testing", M5, "P0", "M", "Suite de testes de sincronização: resiliência a corte de energia (SIGKILL)", ["13.3"],
    "Garantir integridade transacional mesmo com encerramento abrupto.",
    "`SIGKILL` no processo Django/Postgres a meio de uma transacção de teste; validar ausência de dados parciais ao reiniciar.",
    ["Nenhuma escrita parcial visível após reinício, em repetições múltiplas do teste"],
    ["13-testes-e-qualidade.md §13.3.6"])

add("testing", M6, "P1", "L", "Teste de carga de sincronização (volume realista, rede 3G simulada)", ["13.3"],
    "Validar desempenho de sincronização em condições realistas de uma escola grande.",
    "Volume de ~3.000 alunos × notas/faltas de um trimestre, sincronizado sob latência/perda de pacotes simulada (`tc netem`).",
    ["Sincronização completa em tempo aceitável sob as condições simuladas", "Nenhuma perda de dados sob perda de pacotes"],
    ["13-testes-e-qualidade.md §13.3.7"])

add("testing", M6, "P2", "M", "Testes de usabilidade com utilizadores reais por marco", ["13.6"],
    "Validar UX com pessoal real da escola piloto antes de fechar cada marco.",
    "Sessões assistidas medindo tempo de tarefa, erros observados e satisfação (escala 1-5), conforme 13-testes-e-qualidade.md §13.6.",
    ["Sessão realizada antes do fecho de cada marco M1-M6", "Resultados documentados e usados para ajustes de UX"],
    ["13-testes-e-qualidade.md §13.6"])

# =====================================================================
# DEPLOYMENT / OPERATIONS
# =====================================================================

add("infra", M1, "P0", "M", "Setup Wizard de instalação (primeira execução)", ["11.3"],
    "Assistente de instalação que conclui a configuração inicial do Nó Local sem intervenção técnica avançada.",
    "Fluxo completo de 11-implantacao-e-operacoes.md §11.3: SO+Docker → compose up → wizard (Instituição+Gestor) → registo do Node → backup automático.",
    ["Instalação completa por técnico com formação básica em menos de 1 hora (RNF-PORT-03)"],
    ["11-implantacao-e-operacoes.md §11.3"])

add("infra", M5, "P0", "M", "Script de backup diário local cifrado (pg_dump)", ["11.4"],
    "Garantir cópia de segurança local diária, cifrada, com retenção definida.",
    "Cron/Django-Q task executando `pg_dump` cifrado (ex. GPG) diariamente, com rotação de 30 dias.",
    ["Backup diário automático e cifrado", "Restauro testado a partir de um backup gerado pelo script"],
    ["11-implantacao-e-operacoes.md §11.4"])

add("infra", M2, "P2", "S", "Script de shutdown gracioso ao detectar bateria fraca da UPS", ["11.1"],
    "Evitar corrupção de dados em cortes de energia prolongados, mesmo com UPS.",
    "Integração com NUT (Network UPS Tools) ou equivalente, accionando `shutdown` gracioso do container/servidor a um limiar de bateria.",
    ["Encerramento gracioso testado com simulação de bateria baixa"],
    ["11-implantacao-e-operacoes.md §11.1"])

add("infra", M5, "P1", "M", "Monitorização local: painel de saúde (disco, backup, sync)", ["11.5"],
    "Visibilidade operacional básica directamente no Nó Local.",
    "Secção do `admin_panel` mostrando espaço em disco, data do último backup e estado de sincronização.",
    ["Painel mostra os 3 indicadores correctamente"],
    ["11-implantacao-e-operacoes.md §11.5"])

add("infra", M6, "P1", "M", "Monitorização central: métricas agregadas + alertas", ["11.5"],
    "Visibilidade sobre a saúde de todas as instituições geridas pelo Nó Central.",
    "Painel/alerta para nós sem sincronizar há mais de X dias, taxa de erro de sincronização, espaço em disco.",
    ["Alertas accionados correctamente nos cenários definidos"],
    ["11-implantacao-e-operacoes.md §11.5"])

add("infra", MF, "P2", "S", "Procedimento de recuperação de desastre documentado + testado", ["11.6"],
    "Runbook para os 4 cenários de falha descritos (disco, perda total, indisponibilidade central, corrupção de dados).",
    "Documento operacional + simulação real de restauro completo a partir de backup.",
    ["Restauro completo testado com sucesso a partir de backup real"],
    ["11-implantacao-e-operacoes.md §11.6"])

add("infra", M6, "P1", "M", "Pipeline de atualização de versão (migrations automáticas + backup pré-migração)", ["11.7"],
    "Actualizar o Nó Local com janela de indisponibilidade mínima e segurança contra migrações problemáticas.",
    "`docker compose pull && up -d` com passo automático de backup pré-migração e aplicação de migrações no arranque do container.",
    ["Actualização completa em menos de 5 minutos de indisponibilidade", "Backup pré-migração sempre executado antes de aplicar alterações de esquema"],
    ["11-implantacao-e-operacoes.md §11.7"])

add("docs", MF, "P2", "S", "Documentação de suporte técnico em camadas (N1/N2/N3)", ["11.8"],
    "Formalizar o modelo de suporte para operação real das escolas piloto e clientes.",
    "Manual de primeiros socorros para a escola (N1), procedimento de escalonamento para N2/N3, incluindo canal por SMS/telefone.",
    ["Manual N1 entregue às escolas piloto", "Procedimento de escalonamento documentado"],
    ["11-implantacao-e-operacoes.md §11.8"])

# =====================================================================
# LEGISLAÇÃO / COMPLIANCE
# =====================================================================

add("legislacao", M2, "P0", "S", "Parametrizar limites legais de turma (36/45/26) como defaults configuráveis", ["RF-CURR-05"],
    "Reflectir o Decreto Presidencial 162/23 como valor por omissão, mantendo-se configurável.",
    "Valor por omissão em `Turma.numero_maximo_inscritos` + validação de instituição que ultrapasse o tecto legal (aviso, não bloqueio automático).",
    ["Defaults reflectem a legislação vigente", "Instituição pode ajustar com aviso claro quando ultrapassa o valor legal"],
    ["docs/legislacao/README.md (Decreto 162/23)"])

add("legislacao", M2, "P0", "S", "Parametrizar limite de faltas (3× carga semanal) como default configurável", ["RF-FREQ-03"],
    "Reflectir a regra legal de assiduidade como valor por omissão.",
    "Cálculo por omissão `3 * carga_horaria_semanal` em `attendance`, configurável por instituição.",
    ["Valor por omissão reflecte a legislação vigente e é auditável/rastreável à fonte legal"],
    ["docs/legislacao/README.md (Decreto 162/23)"])

add("legislacao", M2, "P0", "XS", "Carregar fixture EscalaAvaliacao oficial (Decreto Executivo 106/26)",
    ["RF-AVAL-03"],
    "(Duplicado propositado em `legislacao` para rastreabilidade de compliance, ver também tarefa em `grading`.)",
    "Fixture `escala_avaliacao.json` conforme docs/legislacao/escala-avaliacao-secundario.md.",
    ["Escala oficial carregada e referenciada a partir da fonte legal documentada"],
    ["docs/legislacao/escala-avaliacao-secundario.md"])

add("legislacao", MF, "P1", "S", "Revisão jurídica formal antes de produção", [],
    "Validar com um jurista especializado em direito angolano da educação e protecção de dados antes do lançamento comercial.",
    "Checklist de conformidade (Lei 17/16, 32/20, Decreto 162/23, Lei 22/11, Lei 12/23) revista por advogado.",
    ["Parecer jurídico obtido e arquivado antes do primeiro lançamento comercial"],
    ["docs/legislacao/README.md (nota de responsabilidade)"])

add("legislacao", MF, "P2", "XS", "Confirmar versão vigente de cada diploma junto do DRE antes do lançamento", [],
    "A legislação angolana é frequentemente actualizada; confirmar que nenhuma norma usada como referência foi revogada/alterada entretanto.",
    "Checklist de verificação junto do Diário da República Eletrónico (dre.gov.ao) antes de cada lançamento major.",
    ["Checklist de verificação executado e documentado antes de cada release major"],
    ["docs/legislacao/README.md"])

# =====================================================================
# FASE 0 / DESCOBERTA
# =====================================================================

add("docs", M0, "P0", "S", "Validação do escopo com instituição piloto real", ["12.1"],
    "Confirmar que o escopo documentado corresponde à realidade operacional de pelo menos uma escola real.",
    "Sessão de validação com Direção/Secretaria de uma escola piloto, revendo os documentos 01-14.",
    ["Documento de confirmação de requisitos assinado pela escola piloto"],
    ["12-plano-de-implementacao.md §12.1"])

add("docs", M0, "P0", "S", "Confirmação da estrutura curricular e fórmula de média praticada na escola piloto", ["12.1"],
    "A legislação nacional dá o enquadramento, mas cada escola pode ter particularidades operacionais na fórmula de cálculo.",
    "Levantamento junto da Direção Pedagógica da escola piloto dos pesos exactos usados (MAC/PT/Exame) e cursos oferecidos.",
    ["Fórmula(s) de média documentada(s) e parametrizável(is) desde o M1"],
    ["12-plano-de-implementacao.md §12.1"])

add("infra", M0, "P0", "XS", "Levantamento de infraestrutura da escola piloto (energia, rede, hardware)", ["12.1"],
    "Dimensionar correctamente o Nó Local a instalar na escola piloto.",
    "Checklist de infraestrutura (energia, UPS existente, rede, hardware disponível) preenchido in loco.",
    ["Checklist preenchido e usado para dimensionar o hardware de referência (11-implantacao-e-operacoes.md §11.1)"],
    ["12-plano-de-implementacao.md §12.1"])

# =====================================================================
# FUTURO / FORA DO ESCOPO v1 (backlog para fases futuras)
# =====================================================================

add("future", MF, "P2", "L", "Módulo de Biblioteca escolar", ["12.9"],
    "Gestão de acervo e empréstimos, identificado como extensão natural do sistema.",
    "Novo app `library` com `Livro`, `Emprestimo`, seguindo os mesmos padrões de `SyncedModel`/tenancy.",
    ["Fora do escopo v1 — manter apenas como item de backlog para fase futura"],
    ["01-visao-geral-e-contexto.md §1.8", "12-plano-de-implementacao.md §12.9"])

add("future", MF, "P2", "M", "Módulo de Cantina/Refeitório", ["12.9"],
    "Gestão de refeições/cartões de aluno, fora do escopo v1.",
    "Novo app `canteen` (nome provisório) com `Refeicao`, `Consumo` por aluno.",
    ["Fora do escopo v1 — manter apenas como item de backlog para fase futura"],
    ["12-plano-de-implementacao.md §12.9"])

add("future", MF, "P2", "M", "Módulo de Transporte Escolar", ["12.9"],
    "Gestão de rotas e alunos transportados, fora do escopo v1.",
    "Novo app `transport` (nome provisório) com `Rota`, `AlunoTransportado`.",
    ["Fora do escopo v1 — manter apenas como item de backlog para fase futura"],
    ["12-plano-de-implementacao.md §12.9"])

add("future", MF, "P2", "L", "Aplicação móvel nativa (iOS/Android)", ["12.9"],
    "Extensão nativa facilitada pela API DRF de sincronização já preparada para o motor offline-first.",
    "App móvel consumindo a mesma API `api/sync` e endpoints de leitura dos portais.",
    ["Fora do escopo v1 — o PWA cobre a necessidade inicial"],
    ["01-visao-geral-e-contexto.md §1.8", "12-plano-de-implementacao.md §12.9"])

add("future", MF, "P2", "M", "Integração directa por API com sistemas do MED", ["12.9"],
    "Dependente da disponibilidade de uma API oficial do Ministério da Educação.",
    "Adapter plugável para submissão automática de relatórios normativos, quando existir especificação oficial.",
    ["Fora do escopo v1 — exportação manual já suportada por RF-ADM-05"],
    ["01-visao-geral-e-contexto.md §1.8", "12-plano-de-implementacao.md §12.9"])

print(f"TOTAL TASKS: {len(TASKS)}")
