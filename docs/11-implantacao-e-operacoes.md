# 11. Implantação e Operações

## 11.1 Requisitos de hardware — Nó Local (por escola)

| Perfil de escola | Hardware recomendado | Especificação mínima |
|---|---|---|
| Pequena (até ~500 alunos) | Mini-PC/NUC ou Raspberry Pi 4/5 (8GB RAM) | 4 núcleos, 8GB RAM, SSD 128GB, Ethernet |
| Média (500–2.000 alunos) | Mini-PC/servidor de secretária | 4–8 núcleos, 16GB RAM, SSD 256GB+, Ethernet |
| Grande (2.000–5.000 alunos) | Servidor de secretária robusto ou VM dedicada | 8 núcleos, 32GB RAM, SSD 512GB (RAID1 recomendado) |

Requisitos transversais recomendados:
- **UPS/Nobreak** obrigatório, dado o histórico de instabilidade eléctrica — dimensionado
  para permitir encerramento gracioso automático (script de shutdown ao detectar bateria
  baixa).
- **Rede local (LAN/Wi-Fi)** cobrindo secretaria, sala de professores e, idealmente,
  salas de aula (para lançamento de faltas/notas em tablet).
- **Router com ligação móvel de backup** (dados móveis Unitel/Movicel/Africell) para as
  janelas de sincronização, mesmo quando não há Internet fixa.

## 11.2 Requisitos — Nó Central (nuvem)

| Escala (n.º de instituições) | VPS recomendado |
|---|---|
| 1–20 escolas | 4 vCPU, 8GB RAM, 100GB SSD |
| 20–100 escolas | 8 vCPU, 16GB RAM, 250GB SSD + Redis dedicado |
| 100+ escolas | Escalar horizontalmente (múltiplas instâncias de app atrás de load balancer, Postgres gerido com réplicas de leitura) |

Fornecedores possíveis: qualquer provedor com boa rota para Angola (testar latência
específica); manter sempre opção de fornecedor com presença/rota regional, dado o
contexto de conectividade internacional variável.

## 11.3 Processo de instalação (Nó Local)

1. Instalar sistema operativo base (Linux Ubuntu Server LTS recomendado).
2. Instalar Docker + Docker Compose.
3. Copiar `docker-compose.local-node.yml` e `.env` (gerado pelo assistente de instalação
   com segredos únicos por instalação).
4. `docker compose up -d` sobe Postgres + Django (Gunicorn) + Nginx + Django-Q.
5. **Setup Wizard** (primeira execução): cria a Instituição e o utilizador Gestor
   (Administrador da Instituição) na mesma transacção — único ponto do sistema onde a
   instituição é seleccionada/criada manualmente (ver
   [04-arquitetura-tecnica.md §4.4.2](04-arquitetura-tecnica.md)).
6. Registo do Node no Nó Central (troca de chave pública, geração de `Node.id`) para
   activar sincronização — pode ser feito mais tarde, sem bloquear o uso local.
7. Configuração de backup automático (ver 11.4).

Tempo-alvo: instalação completa por técnico com formação básica em **menos de 1 hora**
(RNF-PORT-03).

## 11.4 Backups

| Tipo | Frequência | Destino | Retenção |
|---|---|---|---|
| Backup lógico local (`pg_dump` cifrado) | Diário (madrugada, tarefa agendada) | Disco local + disco externo/pen-drive (rotina manual semanal recomendada) | 30 dias locais |
| Backup incremental via sincronização | Contínuo, sempre que há conectividade | Nó Central | Indefinido (é a cópia de continuidade de negócio) |
| Backup completo do Nó Central | Diário | Armazenamento externo (object storage) cifrado | 90 dias + arquivstörio anual |
| Exportação de contingência (`.fsxsync`) | Sob demanda (ausência prolongada de rede) | Pen-drive/transporte físico | Enquanto necessário |

Restauro testado periodicamente (simulação de recuperação de desastre — ver 11.6).

## 11.5 Monitorização e alertas

- **Nó Local**: painel de administração mostra saúde local (espaço em disco, último
  backup, estado de sincronização — ver
  [08-offline-first-e-sincronizacao.md §8.11](08-offline-first-e-sincronizacao.md)).
- **Nó Central**: métricas agregadas de todas as instituições (nós sem sincronizar há
  mais de X dias, taxa de erro de sincronização, espaço em disco), com alerta ao suporte
  técnico central.

## 11.6 Continuidade e recuperação de desastres

| Cenário | Procedimento |
|---|---|
| Falha de disco no Nó Local | Reinstalar sistema, restaurar último backup local ou, na ausência deste, restaurar a partir do Nó Central (dados até à última sincronização) |
| Perda total do servidor da escola (incêndio, roubo) | Provisionar novo hardware, restaurar a partir do Nó Central; apenas alterações não sincronizadas desde o último sync ficam em risco — reforça a importância de sincronização frequente |
| Indisponibilidade do Nó Central | Escolas continuam a operar normalmente offline (por desenho); sincronização retoma automaticamente quando o Nó Central voltar |
| Corrupção de dados detectada | Restaurar de backup íntegro mais recente; investigar causa via logs de auditoria antes de reabrir operação |

## 11.7 Actualizações de versão

- Imagens Docker versionadas (tags semânticas).
- Migrações de base de dados aplicadas automaticamente no arranque do container, com
  backup automático pré-migração.
- Actualização do Nó Local feita preferencialmente durante período não lectivo
  (madrugada/fim-de-semana), com janela de indisponibilidade mínima (`docker compose
  pull && docker compose up -d`, tipicamente < 5 minutos).
- Canal de distribuição de actualizações verificado por assinatura (evita adulteração em
  trânsito).

## 11.8 Suporte técnico

- Modelo de suporte em camadas: **Nível 1** (equipa da escola, com manual básico de
  primeiros socorros: reiniciar serviço, verificar rede/energia), **Nível 2** (equipa
  central FenixSchool, acesso remoto assistido quando há conectividade), **Nível 3**
  (correcção de código/patch).
- Canal de suporte deve funcionar mesmo com conectividade limitada (SMS/chamada
  telefónica como via de escalonamento, não apenas email/chat).
