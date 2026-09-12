# 15. Referências Visuais de UI (Templates Base)

Este documento regista as referências visuais escolhidas para acelerar a implementação do
frontend integrado (Django Templates + HTMX + Alpine.js + Bootstrap 5, sem SPA — ver
[04-arquitetura-tecnica.md §4.6](04-arquitetura-tecnica.md)), evitando desenhar a
interface do zero. Ambos os templates são **baseados em Bootstrap**, o que é directamente
compatível com a stack já decidida em
[10-stack-tecnologica-e-estrutura-projeto.md §10.1](10-stack-tecnologica-e-estrutura-projeto.md).

## 15.1 Área Administrativa — "EduTrack School Dashboard"

- **URL de referência**: https://bootstrapget.com/demos/edu-track-school-dashboard/design/index.html
- **Aplica-se a**: `admin_panel`, e por extensão às áreas internas de secretaria,
  direção pedagógica, financeiro e RH (mesma linguagem visual de painel administrativo).

### O que o template oferece
- Dashboards por papel (escola/professor/aluno) — mapeável directamente ao conceito de
  **painel "Tarefas Actuais" por perfil** já especificado em
  [06-modulos-e-funcionalidades.md §6.15](06-modulos-e-funcionalidades.md).
- Listagens e formulários de gestão de pessoas (professores/alunos) — base visual para
  `enrollment` (Alunos) e `hr` (Funcionários).
- Cartões de curso/turma com indicadores de progresso — reaproveitável em `academic` e
  `grading` (situação da turma, percentagem de aprovação).
- Calendário (vistas de mês/lista, eventos arrastáveis) — base para o calendário escolar
  (`core`/`public-site`) e para o mapa de horários (`academic.Horario`).
- Painéis de notificação e listas de prazos — base visual para `communications` e para o
  painel "Tarefas Actuais".
- Gráficos (Apex/Morris) para analítica — base para os relatórios estatísticos de
  `reports` (RF-REL-05) e para o painel financeiro (RF-FIN-07), a substituir por
  **Chart.js servido localmente** (decisão já tomada em
  [04-arquitetura-tecnica.md §4.6](04-arquitetura-tecnica.md) — não usar a biblioteca de
  gráficos original do template se depender de CDN externo).
- Páginas de autenticação (login) — base visual para o fluxo descrito em
  [09-seguranca-e-privacidade.md §9.2](09-seguranca-e-privacidade.md) (sem campo de
  escola, apenas email/telefone + password).
- Tabelas de dados (DataTables) — usar com moderação: preferir paginação server-side
  simples via Django + HTMX em vez do DataTables completo, para não introduzir
  dependência JS pesada nem reprocessamento client-side de grandes listas (RNF-PERF-02).

### Adaptação necessária (não é um "encaixe directo")
1. Extrair apenas HTML/CSS estático (e ícones) para `static/`; **nenhum JavaScript de
   template SPA-like deve ser adoptado tal e qual** — interatividade é reimplementada com
   HTMX/Alpine.js conforme o padrão do projeto.
2. Sidebar/menu do template mapeado ao menu real de módulos definido em
   [06-modulos-e-funcionalidades.md §6.1](06-modulos-e-funcionalidades.md) (não ao menu
   genérico do template).
3. Substituir qualquer gráfico/ícone/fonte carregado por CDN por versão vendorizada
   localmente (RNF-COMP-02).
4. Simplificar visualmente onde o template for mais denso do que o necessário para
   hardware modesto (RNF-PERF-01).

## 15.2 Área Pública — "Royal College Template"

- **URL de referência**: https://royal-html.netlify.app/ (Royal College Bootstrap
  Template, por Abdus/iamabdus.com)
- **Aplica-se a**: `public_site`.

### O que o template oferece
- Estrutura de site institucional de ensino: hero de boas-vindas, chamada para admissões,
  agendamento de visita ao campus, destaque de cursos, vídeo/testemunhos, notícias/blog,
  pesquisa de cursos com filtros, calendário de eventos, contadores estatísticos
  (alunos/cursos/funcionários), "Porquê escolher-nos", parceiros/logótipos, rodapé com
  contactos — mapeável quase 1:1 ao conjunto de requisitos do portal público:
  - Apresentação institucional e cursos → RF-PUB-01
  - Mural de comunicados/notícias → RF-PUB-02
  - Formulário de pré-candidatura ("Apply Now") → RF-PUB-03
  - Calendário de eventos → calendário escolar (§6.3)
  - Pesquisa de cursos com filtros → adaptável para pesquisa pública de resultados
    minimizada (RF-PUB-04), com os devidos cuidados de privacidade
- Selector de idioma no menu (EN/ES/RU/DE) — **não reaproveitar directamente**: o
  mecanismo de multilinguismo do FenixSchool é o descrito em
  [10-stack-tecnologica-e-estrutura-projeto.md §10.4](10-stack-tecnologica-e-estrutura-projeto.md)
  (português + Umbundu/Kimbundu/Kikongo/Chokwe/Oshikwanyama, preferência pessoal do
  utilizador), não um selector genérico de idiomas internacionais.

### Adaptação necessária
1. Substituir todo o conteúdo de exemplo (cursos, notícias, testemunhos) por dados reais
   vindos de `academic.Curso`, `communications.Aviso`, etc. — nunca deixar conteúdo de
   template por preencher em produção.
2. Remover secções sem correspondência no escopo (loja de cursos tipo e-commerce, blog de
   utilizador genérico) ou adaptá-las apenas ao que for pertinente (mural de notícias).
3. Garantir que o portal público funciona tanto no Nó Central como servido localmente na
   LAN da escola sem Internet (§6.3) — o template, sendo estático, é compatível com isto
   desde que os assets sejam vendorizados localmente.

## 15.3 Licenciamento — pendente de confirmação

**Não foi possível confirmar formalmente a licença de nenhum dos dois templates** a
partir das páginas públicas consultadas (nenhuma delas expõe termos de licença
explícitos; a página de detalhes do EduTrack devolveu erro 403 ao tentar consultar
termos). Antes de vendorizar qualquer asset destes templates no repositório:

- [ ] Confirmar junto da fonte original (bootstrapget.com; iamabdus.com) os termos de uso
  (livre para uso comercial? exige atribuição/backlink? é uma cópia não autorizada de um
  template pago do ThemeForest/ Envato?).
- [ ] Preferir, em caso de dúvida, usar apenas como **referência visual/inspiração de
  layout** (recriando o HTML/CSS do zero com Bootstrap 5 puro) em vez de copiar ficheiros
  directamente, o que elimina qualquer risco de licenciamento.
- [ ] Documentar a licença efectivamente aplicável assim que confirmada, substituindo
  esta secção.

## 15.4 Próximos passos

Tarefas de backlog associadas (GitHub Project #11, labels `module:admin-panel` e
`module:public-site`, fase M1):
- Adoptar o EduTrack como base visual do `admin_panel` (após confirmação de
  licenciamento).
- Adoptar o Royal College Template como base visual do `public_site` (após confirmação de
  licenciamento).
