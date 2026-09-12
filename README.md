# FenixSchool

Sistema de gestão académica para instituições de Ensino Secundário (I e II Ciclo /
Ensino Médio) na República de Angola — construído em Django, com frontend integrado
(sem SPA), funcionamento offline-first e sincronização online/offline sem perda de
dados.

Este projecto recria e expande o escopo do projecto original **Fénix School EM 1.0**
(2017), documentado em [`docs/fenixschoolEM.pdf`](docs/fenixschoolEM.pdf).

## Documentação

Toda a documentação técnica, de requisitos, arquitetura e implementação está em
[`docs/`](docs/00-README.md), incluindo:

- Visão geral, contexto angolano e princípios do projecto
- Requisitos funcionais e não funcionais
- Arquitetura (Nó Local + Nó Central, multi-tenancy, sincronização offline-first)
- Modelo de dados completo
- Perfis, permissões e fluxos de negócio
- Segurança, privacidade e conformidade legal
- Stack tecnológica, plano de implementação, testes
- [Legislação angolana de referência](docs/legislacao/README.md) (educação, protecção de
  dados, trabalho)

Comece por [`docs/00-README.md`](docs/00-README.md).

## Estado actual

Esqueleto inicial do projecto Django (`fenixschool/`) e pacote de documentação de
escopo completo. Implementação das apps de negócio ainda por iniciar — ver roadmap em
[`docs/12-plano-de-implementacao.md`](docs/12-plano-de-implementacao.md).
