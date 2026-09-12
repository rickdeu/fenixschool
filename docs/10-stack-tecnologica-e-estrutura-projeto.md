# 10. Stack Tecnológica e Estrutura do Projeto

## 10.1 Stack

| Camada | Tecnologia | Justificação |
|---|---|---|
| Linguagem | Python 3.12+ | Suporte de longo prazo, ecossistema maduro |
| Framework web | Django 5.x | Monólito modular, Admin embutido, ORM robusto, requisito explícito do cliente |
| Templates/Frontend | Django Template Language + HTMX + Alpine.js + Bootstrap 5 | Frontend integrado sem SPA (requisito explícito) |
| Gráficos | Chart.js (servido localmente) | Painéis de Direção sem dependência de CDN externo |
| API (só sincronização e futuro móvel) | Django REST Framework (DRF) | Padrão de mercado, serializers reutilizáveis para sync |
| Base de dados — Nó Local | PostgreSQL 15+ (ou SQLite 3 em modo WAL para instalações mínimas) | ACID + WAL para resiliência a cortes de energia |
| Base de dados — Nó Central | PostgreSQL 15+ | Multi-tenant, volume maior |
| Tarefas assíncronas — Nó Central | Celery + Redis | Notificações em massa, relatórios pesados |
| Tarefas assíncronas — Nó Local | Django-Q2 (backend em BD, sem Redis) | Reduzir serviços a operar num servidor modesto |
| Geração de PDF | WeasyPrint (HTML/CSS → PDF) | Reutiliza os mesmos templates Django para ecrã e para PDF |
| Auditoria/Histórico | App própria `audit` (signals) + `django-simple-history` como opção de reforço em modelos críticos | Rastreabilidade legal |
| Autenticação 2FA | `django-otp` (TOTP) | Funciona offline, sem dependência de SMS |
| Cifra de campo | `django-cryptography` (ou `django-fernet-fields`) | Protecção de dados sensíveis em repouso |
| Servidor de aplicação | Gunicorn | Padrão robusto para Django em produção |
| Proxy reverso / estáticos | Nginx (+ WhiteNoise como fallback simplificado) | TLS termination, serve estáticos eficientemente |
| Containerização | Docker + Docker Compose | Instalação e actualização reprodutíveis em qualquer hardware |
| CI | GitHub Actions (ou GitLab CI, conforme alojamento do repositório) | Lint, testes, build de imagem |
| Observabilidade | `django-structlog` (logs estruturados locais) + Sentry auto-hospedado (opcional, Nó Central) | RNF-OBS-01/03 |
| Qualidade de código | `ruff` (lint+format), `mypy` (opcional), `pytest` + `pytest-django` | RNF-MAN-01/03 |

## 10.2 Estrutura de diretórios do projeto

```
fenixschool/
├── manage.py
├── pyproject.toml
├── docker-compose.yml
├── docker-compose.local-node.yml
├── docker-compose.central-node.yml
├── .env.example
├── config/                         # settings Django
│   ├── settings/
│   │   ├── base.py
│   │   ├── local_node.py
│   │   ├── central_node.py
│   │   └── test.py
│   ├── urls.py
│   └── wsgi.py / asgi.py
├── apps/
│   ├── core/                       # Instituicao, AnoLectivo, mixins (SyncedModel, TenantQuerySet)
│   ├── accounts/                   # Utilizador, Perfil, autenticação, 2FA
│   ├── academic/                   # Departamento, Curso, Disciplina, Turma, Horario, Sala
│   ├── enrollment/                 # Aluno, Candidato, EncarregadoEducacao, Matricula
│   ├── grading/                    # TipoAvaliacao, Nota, Pauta, EscalaAvaliacao
│   ├── attendance/                 # Presenca, Justificacao
│   ├── finance/                    # TabelaPrecos, Mensalidade, Pagamento
│   ├── hr/                         # Funcionario, Seccao, Cargo, Contrato
│   ├── communications/             # Aviso, Notificacao
│   ├── reports/                    # Geração de PDFs oficiais
│   ├── public_site/                # Portal público
│   ├── student_portal/             # Portal do aluno
│   ├── guardian_portal/            # Portal do encarregado
│   ├── admin_panel/                # Área administrativa restrita
│   ├── sync/                       # RegistoAlteracao, SessaoSincronizacao, Conflito, Node
│   ├── audit/                      # RegistoAuditoria
│   └── api/                        # DRF — endpoints de sincronização
├── static/
│   ├── css/  (Bootstrap customizado)
│   ├── js/   (HTMX, Alpine.js, Chart.js — vendorizados localmente)
│   └── img/
├── templates/
│   ├── base.html
│   ├── components/                 # partials reutilizáveis (HTMX fragments)
│   └── <app>/...                   # também replicado dentro de cada app
├── locale/
│   └── pt_AO/                      # traduções e formatos locais
├── fixtures/
│   ├── provincias_municipios.json
│   ├── operadoras_moveis.json
│   ├── tipos_documento.json
│   └── escala_avaliacao.json
└── tests/
    ├── unit/
    ├── integration/
    └── sync_partition/              # testes de partição de rede (ver doc 13)
```

Cada app segue internamente o padrão:

```
apps/<app>/
├── models.py (ou models/ se muitos modelos)
├── services.py            # regras de negócio, transações
├── forms.py
├── views.py
├── urls.py
├── admin.py                # registo no Django Admin
├── signals.py              # disparo de changelog/auditoria
├── permissions.py          # âmbito de acesso por perfil
├── templates/<app>/
└── tests/
```

## 10.3 Ambientes

| Ambiente | Propósito | Configuração |
|---|---|---|
| Desenvolvimento | Máquina do programador | SQLite ou Postgres local via Docker, `DEBUG=True` |
| Homologação | Validação com escola piloto antes de produção | Réplica da configuração de Nó Local, dados de teste |
| Produção — Nó Local | Servidor físico da escola | `config.settings.local_node`, Postgres, Django-Q, sem Celery/Redis |
| Produção — Nó Central | Nuvem | `config.settings.central_node`, Postgres, Celery+Redis, DRF de sincronização activo |

## 10.4 Multilinguismo (i18n) — implementação técnica

Requisito: RNF-LOC-06/07/08 ([03-requisitos-nao-funcionais.md](03-requisitos-nao-funcionais.md)).

### 10.4.1 Mecanismo

- Usa-se o próprio subsistema de internacionalização do Django (`django.utils.translation`,
  `{% trans %}`/`{% blocktrans %}` nos templates, `gettext` no código Python), **sem
  bibliotecas externas de tradução**, coerente com o princípio de frontend integrado.
- Como o Django **não** inclui catálogos de tradução para línguas nacionais angolanas
  (não fazem parte do conjunto de *locales* oficialmente mantidos pelo projecto Django),
  é necessário criar e manter catálogos próprios em `locale/<código>/LC_MESSAGES/django.po`
  para cada uma: `pt` (base/origem das strings), `umb`, `kmb`, `kon`, `cjk`, `kua`.
- `LANGUAGES` em `settings/base.py`:

```python
LANGUAGES = [
    ("pt", "Português"),
    ("umb", "Umbundu"),
    ("kmb", "Kimbundu"),
    ("kon", "Kikongo"),
    ("cjk", "Chokwe"),
    ("kua", "Oshikwanyama"),
]
LANGUAGE_CODE = "pt"
LOCALE_PATHS = [BASE_DIR / "locale"]
```

- `django.middleware.locale.LocaleMiddleware` resolve o idioma **a partir da preferência
  gravada no perfil do utilizador autenticado** (não do cabeçalho `Accept-Language` do
  navegador, que seria pouco fiável neste contexto) — implementado com um middleware fino
  próprio que chama `translation.activate(request.user.idioma_preferido)` logo após a
  autenticação, antes do `LocaleMiddleware` padrão actuar sobre utilizadores anónimos
  (que usam `pt` por omissão no Portal Público).
- Selector de idioma visível no cabeçalho de todas as páginas autenticadas (dropdown
  simples, sem JavaScript pesado — form HTML padrão com Alpine.js apenas para o
  toggle visual).

### 10.4.2 Fluxo de tradução (processo humano, não só técnico)

Dado que não existem catálogos prontos para estas línguas, o projecto deve prever:
1. Extracção das strings de origem (`django-admin makemessages -l umb -l kmb -l kon -l cjk -l kua`).
2. Tradução por falantes nativos/linguistas colaboradores — recomenda-se parceria com o
   Instituto de Línguas Nacionais (ILN) ou docentes de língua nacional das próprias
   escolas piloto, que já lidam com estas línguas no ensino.
3. Revisão terminológica (termos escolares como "matrícula", "nota", "turma" podem não
   ter tradução directa consolidada — decisão editorial de manter o termo em português
   com glossário de apoio, quando não houver termo nacional estabelecido, evitando
   neologismos confusos).
4. Compilação (`django-admin compilemessages`) integrada no processo de build/deploy.
5. Processo incremental: v1 pode lançar com cobertura parcial (ex. 100% dos menus e
   ecrãs mais usados: login, matrícula, notas, financeiro) e completar as restantes
   strings em iterações seguintes — melhor ter 5 línguas a 80% do que 1 língua a 100% e
   nada nas restantes, dado o objectivo de inclusão.

### 10.4.3 Âmbito da tradução

| Elemento | Traduzido? |
|---|---|
| Menus, botões, rótulos de formulário, mensagens de erro/sucesso | Sim — via `gettext` |
| Nomes de disciplinas/cursos/turmas cadastrados pela escola | Não — conteúdo da instituição, mantido tal como inserido |
| Avisos/comunicados publicados pela escola | Não (é conteúdo livre do operador; a escola pode optar por publicar em mais de uma língua manualmente, criando múltiplos avisos) |
| Documentos oficiais em PDF (certificados, declarações, pautas) | Não — mantidos em português por validade legal/administrativa (RNF-LOC-08) |
| Portal Público institucional | Sim, nos elementos fixos de navegação; o conteúdo institucional (missão, apresentação) é escrito pela escola e pode opcionalmente ser fornecido em múltiplas línguas pela própria instituição |

### 10.4.4 Modelo de dados associado

Ver também [05-modelo-de-dados.md](05-modelo-de-dados.md):
- `accounts.Utilizador.idioma_preferido` (choice, um dos códigos de `LANGUAGES`, por
  omissão `pt`).
- Sem qualquer campo de idioma em `core.Instituicao` — reforça que o idioma é sempre
  escolha individual (RNF-LOC-07), nunca imposta pela escola/Nó.

## 10.5 Convenções de código

- PEP 8 + `ruff format` como formatador único (evita divergência de estilo).
- Nomes de modelos, campos e mensagens de utilizador em português (domínio de negócio
  angolano); nomes de variáveis técnicas internas podem seguir inglês onde for idiomático
  ao Django (ex.: `Meta`, `save()`), mantendo consistência com o próprio framework.
  Diretriz: código-domínio (models de negócio) em português; infraestrutura genérica
  reutilizável (mixins técnicos, utilitários de sync) pode usar inglês quando facilita
  reutilização/leitura por terceiros familiarizados com Django.
- Migrações sempre revistas manualmente antes de aplicar em produção (nunca
  `makemigrations` cego em cima de dados reais).
- Commits pequenos e descritivos; testes acompanham a mesma alteração que a motivou.
