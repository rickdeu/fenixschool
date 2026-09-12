# 09. Segurança e Privacidade

Base legal: [Lei n.º 22/11, de 17 de Junho — Lei de Protecção de Dados Pessoais](legislacao/lei-22-11-protecao-dados-pessoais.pdf)
(ver [índice de legislação](legislacao/README.md)). Este documento traduz os princípios
legais em requisitos técnicos concretos para o FenixSchool.

## 9.1 Princípios da Lei 22/11 aplicados ao sistema

| Princípio legal | Tradução técnica no FenixSchool |
|---|---|
| Licitude e finalidade determinada | Cada campo de dados pessoais recolhido está ligado a uma finalidade documentada (ex.: contacto para comunicação escolar, não para marketing) |
| Proporcionalidade / minimização | Formulários de inscrição/candidatura só pedem os campos estritamente necessários; nenhum campo especulativo "para o futuro" |
| Consentimento (dados de menores) | O acto de Inscrição de um Aluno exige a associação de um Encarregado de Educação, cujo consentimento é registado (checkbox + timestamp) no momento da inscrição |
| Direito de acesso e rectificação | O portal do Encarregado/Aluno permite consulta dos próprios dados e pedido de rectificação (via Secretaria); o Administrador da Instituição tem ecrã de exportação de dados de um titular a pedido |
| Segurança da informação | Cifra em trânsito (TLS) e em repouso para campos críticos (ver 9.3); RBAC; auditoria (ver 9.4) |
| Conservação limitada | Dados técnicos (logs) com retenção definida (RNF-AUD-03); dados académicos mantidos pelo tempo exigido pelo histórico escolar (indefinido, por natureza do registo educativo) |
| Responsável pelo tratamento | Cada instituição é responsável pelos dados dos seus alunos/funcionários; o operador da plataforma (Nó Central) actua como subcontratante técnico quando aplica sincronização/backup |

## 9.2 Autenticação e controlo de acesso

- Login por email ou telefone + password (nunca por selecção manual de instituição — ver
  [04-arquitetura-tecnica.md §4.4.4](04-arquitetura-tecnica.md)).
- Password: hashing Argon2 (via Django `PASSWORD_HASHERS`), política mínima de robustez
  (comprimento, não reutilização de passwords comprometidas conhecidas via lista
  offline, sem exigir complexidade artificial excessiva que leve a más práticas).
- **2FA (TOTP)** obrigatório para perfis Administrador da Instituição, Super
  Administrador e Financeiro/Tesouraria; opcional para os restantes. TOTP funciona
  offline (não depende de SMS/rede).
- Bloqueio progressivo de conta após tentativas falhadas repetidas (protecção contra
  força bruta), com desbloqueio administrativo.
- Sessões com expiração automática por inactividade, configurável por perfil (mais
  curta para perfis administrativos/financeiros).
- RBAC (Role-Based Access Control) via Django Groups/Permissions + âmbito por objecto
  (ver matriz completa em
  [07-perfis-permissoes-e-fluxos.md](07-perfis-permissoes-e-fluxos.md)).

## 9.3 Protecção de dados em repouso e em trânsito

| Camada | Medida |
|---|---|
| Rede (browser ↔ servidor local, local ↔ central) | TLS 1.2+ obrigatório; certificado auto-assinado interno aceitável na LAN da escola (com distribuição do certificado raiz aos dispositivos da instituição), certificado público válido no Nó Central |
| Sincronização Nó Local ↔ Nó Central | Autenticação mútua por chave/token do Node (ver [08-offline-first-e-sincronizacao.md §8.5](08-offline-first-e-sincronizacao.md)) além do TLS |
| Campos sensíveis em repouso | Número de documento de identificação (BI/Passaporte), contactos directos de encarregados e dados de saúde/necessidades educativas especiais (quando aplicável) cifrados a nível de campo (`django-cryptography` ou equivalente) na base de dados local e central |
| Ficheiros (fotos, anexos de justificação de falta) | Armazenamento em disco com permissões restritas; acesso mediado sempre pela aplicação (nunca URL directa pública) |
| Pacotes de contingência (`.fsxsync`) | Cifrados end-to-end com a chave do Node de destino — mesmo um pen-drive extraviado não expõe dados |
| Backups | Cifrados em repouso (ver [11-implantacao-e-operacoes.md](11-implantacao-e-operacoes.md)) |

## 9.4 Auditoria

- Toda alteração/eliminação (soft-delete) a Notas, Matrículas, Pagamentos, Utilizadores e
  Permissões grava uma entrada em `audit.RegistoAuditoria` com utilizador, timestamp, IP
  de origem, valores antes/depois.
- O painel de auditoria (RF-ADM-03) permite pesquisa por entidade, utilizador, período.
- Registos de auditoria são **imutáveis** (sem update/delete disponível via aplicação;
  apenas rotina de retenção administrada directamente na base de dados, fora do fluxo
  normal).

## 9.5 Gestão de incidentes

- Procedimento documentado de resposta a incidente (perda de dispositivo, acesso
  indevido suspeito, comprometimento de conta): suspensão imediata da conta afectada,
  análise do log de auditoria, notificação ao Administrador da Instituição.
- Em caso de violação de dados pessoais com risco para os titulares, a instituição
  (enquanto responsável pelo tratamento) deve ser apoiada pelo sistema com um relatório
  de âmbito do incidente (que dados, quantos titulares, período), para cumprir eventuais
  obrigações de notificação nos termos da Lei 22/11.

## 9.6 Segurança física e operacional do Nó Local

Dado que o servidor de cada escola guarda dados sensíveis de menores:
- Recomenda-se que o servidor local fique em local de acesso restrito (não na sala de
  aula, não acessível ao público).
- Conta de sistema operativo dedicada, sem partilha de credenciais de infraestrutura com
  utilizadores finais da aplicação.
- Actualizações de segurança do sistema operativo e da stack aplicadas em rotina
  (ver [11-implantacao-e-operacoes.md](11-implantacao-e-operacoes.md)).

## 9.7 Segurança no ciclo de desenvolvimento

- Revisão de código obrigatória antes de merge (mesmo em equipa pequena).
- Dependências geridas com verificação de vulnerabilidades conhecidas (`pip-audit` em
  CI).
- Testes de segurança básicos incluídos na suite (protecção CSRF nativa do Django,
  cabeçalhos de segurança HTTP — `django-csp`, `SECURE_*` settings, protecção contra
  SQL injection garantida pelo uso exclusivo do ORM, sanitização de uploads).
- Segredos (chaves, credenciais de BD) nunca em código-fonte; geridos por variáveis de
  ambiente/`django-environ` e nunca commitados.
