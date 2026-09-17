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
