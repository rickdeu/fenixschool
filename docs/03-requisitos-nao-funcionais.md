# 03. Requisitos Não Funcionais

Convenção: `RNF-<CATEGORIA>-<NÚMERO>`.

## 3.1 Disponibilidade e Resiliência Offline

| ID | Requisito |
|---|---|
| RNF-DISP-01 | O nó local deve garantir 100% de disponibilidade das funções essenciais (inscrição, matrícula, notas, financeiro) independentemente do estado da ligação à Internet. |
| RNF-DISP-02 | A base de dados local deve usar um motor com garantias ACID e *write-ahead logging* (PostgreSQL local, ou SQLite em modo WAL para instalações mínimas) para tolerar cortes de energia sem corrupção. |
| RNF-DISP-03 | O sistema deve detectar automaticamente a perda e o retorno de conectividade, sem exigir reinício manual dos serviços. |
| RNF-DISP-04 | Uma falha na sincronização não deve nunca bloquear ou degradar a operação local. |
| RNF-DISP-05 | Objetivo de continuidade: RPO (Recovery Point Objective) local ≤ 1 transação (praticamente zero perda, dado o uso de BD transacional local); RPO de sincronização com o nó central ≤ 24h em condições normais de conectividade. |

## 3.2 Desempenho

| ID | Requisito |
|---|---|
| RNF-PERF-01 | Páginas do nó local devem carregar em < 1,5s em hardware modesto (ver [11-implantacao-e-operacoes.md](11-implantacao-e-operacoes.md)) em rede local (LAN/Wi-Fi). |
| RNF-PERF-02 | Operações de listagem (alunos, notas, pagamentos) devem suportar paginação e permanecer responsivas com até 5.000 alunos matriculados por instituição. |
| RNF-PERF-03 | A sincronização deve transmitir apenas deltas (alterações), nunca o dataset completo, para minimizar consumo de dados móveis. |
| RNF-PERF-04 | Geração de relatórios/documentos PDF individuais deve completar em < 3s; relatórios em lote (pautas de turma) em < 15s para turmas de até 60 alunos. |

## 3.3 Segurança

Ver aprofundamento em [09-seguranca-e-privacidade.md](09-seguranca-e-privacidade.md).

| ID | Requisito |
|---|---|
| RNF-SEC-01 | Toda comunicação entre navegador e servidor, e entre nó local e nó central, deve usar TLS 1.2+. |
| RNF-SEC-02 | Palavras-passe devem ser armazenadas com hashing forte (Argon2/PBKDF2 via Django) e nunca em texto plano, mesmo localmente. |
| RNF-SEC-03 | O acesso a dados de menores e a documentos de identificação deve ser restrito por perfil (RBAC), com princípio do menor privilégio. |
| RNF-SEC-04 | Todas as ações de alteração/eliminação sobre notas, matrículas, pagamentos e utilizadores devem gerar registo de auditoria imutável. |
| RNF-SEC-05 | O sistema deve suportar autenticação de dois factores (2FA) para perfis de administração e financeiro, mesmo em modo offline (TOTP não depende de rede). |
| RNF-SEC-06 | Dados sensíveis (n.º de BI, contactos) devem ser cifrados em repouso nos campos considerados críticos, mesmo na base local. |

## 3.4 Escalabilidade

| ID | Requisito |
|---|---|
| RNF-ESC-01 | A arquitetura deve suportar de 1 a várias centenas de instituições geridas a partir de um único nó central, sem alteração estrutural. |
| RNF-ESC-02 | O nó local deve suportar até ~3.000 alunos e ~150 funcionários numa instalação de referência (single-server) sem degradação perceptível. |
| RNF-ESC-03 | O modelo de dados deve usar identificadores (UUID) que permitam fusão de dados de múltiplos nós locais no nó central sem colisão. |

## 3.5 Usabilidade e Acessibilidade

| ID | Requisito |
|---|---|
| RNF-USA-01 | A interface deve ser utilizável por pessoal com literacia digital básica, com fluxos guiados e mensagens de erro em português claro. |
| RNF-USA-02 | O sistema deve seguir directrizes WCAG 2.1 nível AA nos ecrãs públicos e de portal (contraste, navegação por teclado, texto alternativo). |
| RNF-USA-03 | O sistema deve ser responsivo (mobile-first) para os portais de aluno/encarregado, dado o uso predominante de smartphones para acesso externo. |
| RNF-USA-04 | Os formulários mais usados (inscrição, matrícula, lançamento de notas, registo de pagamento) devem ser optimizados para o menor número de cliques/ecrãs possível. |

## 3.6 Compatibilidade

| ID | Requisito |
|---|---|
| RNF-COMP-01 | O sistema deve funcionar correctamente nas duas últimas versões principais de Chrome, Firefox e Edge, e em navegadores móveis Android comuns (Chrome Mobile). |
| RNF-COMP-02 | O sistema deve degradar graciosamente em conexões lentas (2G/3G): imagens optimizadas, sem dependências de CDN externas obrigatórias (assets servidos localmente). |
| RNF-COMP-03 | Documentos oficiais gerados devem imprimir correctamente em impressoras térmicas/jacto de tinta comuns em formato A4. |

## 3.7 Localização (i18n/l10n) e Multilinguismo

| ID | Requisito |
|---|---|
| RNF-LOC-01 | Idioma por omissão: português (Angola) — `pt-AO` (fallback `pt`, dado que o Django não inclui `pt-AO` nativamente; será criado *locale* próprio). |
| RNF-LOC-02 | Moeda: Kwanza (AOA), com formatação `Kz 1.234.567,89`. |
| RNF-LOC-03 | Fuso horário: `Africa/Luanda` (WAT, UTC+1, sem horário de verão). |
| RNF-LOC-04 | Formato de data: `dd/mm/aaaa`. |
| RNF-LOC-05 | Listas de referência (províncias e municípios de Angola, operadoras móveis, tipos de documento de identificação) devem estar pré-carregadas como dados de sistema (fixtures). |
| RNF-LOC-06 | O sistema deve ser **multilíngue**: português como idioma por omissão e obrigatório (idioma de trabalho oficial e legal, ver Lei 17/16), mais **pelo menos 5 línguas nacionais angolanas** como opção de interface para alunos, encarregados de educação e funcionários que as prefiram. |
| RNF-LOC-07 | A troca de idioma deve ser uma preferência **pessoal** do utilizador (campo `idioma_preferido` em `accounts.Utilizador`), nunca uma configuração de todo o Nó/Instituição — dois utilizadores da mesma escola podem usar idiomas de interface diferentes em simultâneo. |
| RNF-LOC-08 | Conteúdo gerado pela instituição (nome de cursos/disciplinas, avisos/comunicados, textos de documentos oficiais) permanece na língua em que foi escrito pelo operador; apenas os **textos fixos da interface** (rótulos, botões, mensagens de sistema, menus) são traduzidos automaticamente conforme a preferência de idioma. Documentos oficiais (certificados, declarações, pautas) mantêm-se em português, por ser o idioma oficial de validade legal/administrativa. |

### 3.7.1 Línguas nacionais suportadas (mínimo v1)

Seleccionadas por serem as línguas nacionais angolanas com maior número de falantes,
segundo distribuição regional amplamente reconhecida:

| Língua | Código ISO 639-3 | Região predominante |
|---|---|---|
| Umbundu | `umb` | Planalto Central (Huambo, Bié, Benguela) |
| Kimbundu | `kmb` | Luanda, Bengo, Malanje |
| Kikongo | `kon` | Norte (Uíge, Zaire, Cabinda) |
| Chokwe (Tchokwe) | `cjk` | Leste (Lunda Norte, Lunda Sul, Moxico) |
| Oshikwanyama | `kua` | Sul (Cunene) |

Lista extensível (arquitectura preparada para adicionar Nganguela, Olunyaneka, Fiote,
Muhumbi, entre outras, sem alteração estrutural — ver 10.5 em
[10-stack-tecnologica-e-estrutura-projeto.md](10-stack-tecnologica-e-estrutura-projeto.md)).

## 3.8 Auditabilidade e Conformidade

| ID | Requisito |
|---|---|
| RNF-AUD-01 | O sistema deve manter histórico completo (quem/quando/valor anterior/valor novo) para entidades críticas: Nota, Matrícula, Pagamento, Utilizador, Permissão. |
| RNF-AUD-02 | O sistema deve cumprir a Lei n.º 22/11 (Lei de Proteção de Dados Pessoais de Angola): minimização de dados, finalidade declarada, consentimento do encarregado de educação para tratamento de dados de menores, direito de acesso e rectificação. |
| RNF-AUD-03 | Registos de auditoria devem ser preservados por, no mínimo, o tempo legal de conservação de registos escolares (recomendado: indefinido para o histórico escolar; 5 anos para logs técnicos). |

## 3.9 Manutenibilidade

| ID | Requisito |
|---|---|
| RNF-MAN-01 | O código deve seguir PEP 8, com formatação automática (black/ruff) e verificação estática (mypy opcional) em CI. |
| RNF-MAN-02 | Cada app Django deve ser coesa e desacoplada, comunicando por interfaces claras (services/signals), permitindo substituição/evolução independente. |
| RNF-MAN-03 | Cobertura de testes automatizados mínima de 70% no núcleo de negócio (matrícula, notas, financeiro, sincronização). |
| RNF-MAN-04 | Migrações de base de dados devem ser reversíveis e testadas antes de aplicação em produção. |

## 3.10 Portabilidade e Custo Operacional

| ID | Requisito |
|---|---|
| RNF-PORT-01 | O nó local deve correr em hardware de baixo custo (mini-PC/NUC ou equivalente; Raspberry Pi 4/5 como opção mínima para escolas muito pequenas). |
| RNF-PORT-02 | A stack deve ser 100% baseada em software livre/open source, sem custos de licenciamento recorrentes. |
| RNF-PORT-03 | A instalação/actualização do nó local deve ser possível por uma pessoa com formação técnica básica, via script/Docker Compose, em menos de 1 hora. |

## 3.11 Observabilidade

| ID | Requisito |
|---|---|
| RNF-OBS-01 | O sistema deve registar logs estruturados localmente, rotacionados automaticamente, sem depender de serviço externo. |
| RNF-OBS-02 | O nó central deve expor métricas de saúde (uptime, latência, filas de sincronização) para monitorização. |
| RNF-OBS-03 | Erros de aplicação devem poder ser reportados a um serviço de rastreio de erros (ex.: Sentry auto-hospedado) quando disponível conectividade, sem bloquear a operação offline. |

## 3.12 Matriz de Priorização (resumo)

| Categoria | Nível de exigência | Justificação |
|---|---|---|
| Offline-first / Disponibilidade | Crítico | Requisito estruturante do projeto, imposto pela realidade angolana |
| Segurança de dados pessoais | Crítico | Dados de menores + obrigação legal |
| Desempenho em hardware modesto | Alto | Parque informático heterogéneo |
| Escalabilidade multi-instituição | Médio | Necessário para viabilidade comercial, não bloqueante do MVP |
| Acessibilidade WCAG | Médio | Boa prática, não bloqueante do MVP |
