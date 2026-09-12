# FenixSchool — Documentação Técnica e de Implementação

Sistema de gestão académica para instituições de Ensino Secundário (I e II Ciclo /
Ensino Médio) na República de Angola. Este pacote de documentação recria e expande o
escopo do projecto original **Fénix School EM 1.0** (2017), cujos artefactos de código
foram perdidos, com base no documento de referência preservado
([`fenixschoolEM.pdf`](fenixschoolEM.pdf)), e define a solução completa a construir em **Django**, com
frontend integrado (sem SPA), funcionamento **offline-first** e sincronização
online/offline sem perda de dados.

## Como navegar este pacote

| # | Documento | Conteúdo |
|---|---|---|
| 01 | [Visão Geral e Contexto](01-visao-geral-e-contexto.md) | Origem do projecto, objectivos, contexto angolano, princípios orientadores, escopo, marcos macro |
| 02 | [Requisitos Funcionais](02-requisitos-funcionais.md) | Requisitos por módulo (RF-*), com prioridade MoSCoW |
| 03 | [Requisitos Não Funcionais](03-requisitos-nao-funcionais.md) | Disponibilidade offline, desempenho, segurança, multilinguismo, localização, auditabilidade |
| 04 | [Arquitetura Técnica](04-arquitetura-tecnica.md) | Nó Local + Nó Central, monólito modular Django, multi-tenancy e onboarding automático, ADRs |
| 05 | [Modelo de Dados](05-modelo-de-dados.md) | Entidades completas (expandidas do documento original), diagrama ER |
| 06 | [Módulos e Funcionalidades](06-modulos-e-funcionalidades.md) | Mapa de módulos por portal/área de acesso, fluxos de uso |
| 07 | [Perfis, Permissões e Fluxos](07-perfis-permissoes-e-fluxos.md) | Matriz de permissões por perfil, sequências dos fluxos-chave |
| 08 | [Offline-First e Sincronização](08-offline-first-e-sincronizacao.md) | Motor de sincronização, resolução de conflitos, modo de contingência sem rede |
| 09 | [Segurança e Privacidade](09-seguranca-e-privacidade.md) | Conformidade com a Lei 22/11, autenticação, cifra, auditoria |
| 10 | [Stack Tecnológica e Estrutura do Projeto](10-stack-tecnologica-e-estrutura-projeto.md) | Tecnologias, estrutura de diretórios, ambientes, implementação de multilinguismo |
| 11 | [Implantação e Operações](11-implantacao-e-operacoes.md) | Hardware, instalação, backups, continuidade de negócio |
| 12 | [Plano de Implementação](12-plano-de-implementacao.md) | Roadmap por marcos (M1–M6), critérios de aceitação |
| 13 | [Testes e Qualidade](13-testes-e-qualidade.md) | Estratégia de testes, com foco especial em testes de sincronização |
| 14 | [Glossário](14-glossario.md) | Termos de negócio angolanos e termos técnicos de arquitetura |
| 15 | [Referências Visuais de UI](15-referencias-visuais-ui.md) | Templates Bootstrap escolhidos como base visual do admin_panel e do public_site |
| — | [Legislação de Referência](legislacao/README.md) | Leis e decretos angolanos aplicáveis (educação, protecção de dados, trabalho), com PDFs oficiais |

## Como este pacote deve ser lido

- **Visão de negócio/produto** (patrocinador, direcção escolar): documentos 01, 02, 06,
  12.
- **Arquitectura e decisões técnicas** (equipa de engenharia): documentos 04, 05, 08, 09,
  10.
- **Operação e suporte**: documento 11.
- **Conformidade legal**: pasta `legislacao/` + documento 09.

## Princípios inegociáveis do projeto

1. O sistema **nunca** pode depender de Internet para operar no dia-a-dia de uma escola.
2. **Nenhum dado é perdido**, mesmo com falhas de energia, rede ou hardware.
3. O frontend é **Django integrado** — sem React, Vue ou qualquer SPA.
4. Ninguém, em uso normal, escolhe manualmente "a que escola pertence" — a instituição é
   sempre resolvida automaticamente a partir de quem cadastrou o utilizador.
5. Português é obrigatório; línguas nacionais são um direito de escolha pessoal, não uma
   configuração institucional.

## Estado deste pacote

Documentação de escopo completo para arranque de implementação (Fase 0 concluída ao
nível de especificação). Próximo passo natural: iniciar a Fase 1 (Fundação) descrita em
[12-plano-de-implementacao.md](12-plano-de-implementacao.md), incluindo a criação efectiva
do projecto Django (`fenixschool/`) fora desta pasta `docs/`.
