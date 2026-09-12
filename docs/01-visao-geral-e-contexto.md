# 01. Visão Geral e Contexto

## 1.1 Origem do projeto

Este pacote de documentação retoma e expande o projeto **Fénix School EM 1.0**, descrito no
documento original (`fenixschoolEM.pdf`, JJ Hangalo / Fenix Innovation, actualizado em
06.10.2017). O sistema original era uma aplicação web para gestão do processo escolar de
instituições do Ensino Médio angolano, com módulos de Inscrições, Matrículas, Currículo,
Funcionários, Tabelas, Área Académica, Gestão de Notas e Relatórios.

Os artefactos de código-fonte do projeto original foram perdidos. Este documento **recria o
escopo do zero**, aproveitando os conceitos de negócio, o modelo de dados e os fluxos já
validados no documento original, e propõe uma nova solução técnica — **FenixSchool** —
construída em **Django**, com frontend integrado (sem framework de SPA como React ou Vue) e
capacidade de funcionamento **offline-first com sincronização**, adequada à realidade angolana.

## 1.2 Apresentação do novo sistema

**FenixSchool** é uma aplicação de gestão escolar para instituições de Ensino Secundário
(1.º e 2.º Ciclo, incluindo o Ensino Médio Técnico-Profissional e Pré-Universitário) na
República de Angola, cobrindo o processo escolar anual nas vertentes administrativa,
pedagógica, financeira e de recursos humanos, com portais públicos de comunicação com
encarregados de educação, alunos e comunidade em geral.

## 1.3 Objetivos do projeto

Retomados e expandidos a partir do documento original:

1. Implementar uma aplicação que cubra todos os segmentos do processo escolar nas
   vertentes administrativa e pedagógica (inscrição, matrícula, currículo, avaliação,
   frequência, financeiro, recursos humanos, comunicação e relatórios oficiais).
2. Oferecer às instituições de ensino médio uma ferramenta eficiente, nacional e a preço
   de concorrência, com assistência garantida.
3. **Funcionar de forma fiável mesmo sem ligação permanente à Internet**, sem perda de
   dados, sincronizando automaticamente sempre que a conectividade estiver disponível.
4. Disponibilizar áreas de acesso diferenciadas: público em geral, encarregados de
   educação, alunos, pessoal das diferentes secções (secretaria, direção pedagógica,
   financeira/tesouraria, recursos humanos) e administração restrita do sistema.
5. Respeitar a legislação angolana de proteção de dados pessoais e os requisitos
   normativos do Ministério da Educação (MED).

## 1.4 Contexto do Ensino Secundário em Angola

O sistema deve refletir a estrutura curricular angolana em vigor (Reforma Educativa):

- **Ensino Primário**: 1.ª à 6.ª classe (fora do escopo direto, mas pode coexistir na
  mesma instituição).
- **I Ciclo do Ensino Secundário**: 7.ª à 9.ª classe.
- **II Ciclo do Ensino Secundário** (Ensino Médio): 10.ª à 13.ª classe, organizado por
  cursos/áreas de formação (ex.: Ciências Físicas e Biológicas, Ciências Económicas e
  Jurídicas, Humanidades, Artes Visuais, Informática, Contabilidade e Gestão, entre
  outros, consoante o Instituto/Escola).
- **Ano Lectivo**: dividido em Trimestres (o padrão mais comum) ou Semestres, consoante o
  calendário escolar publicado anualmente pelo MED.
- **Escala de avaliação**: 0 a 20 valores, com nota mínima de aprovação geralmente 10.
- **Componentes de avaliação**: MAC (Média de Avaliação Contínua), Provas Trimestrais/PT,
  Exame Final — a fórmula exacta de cálculo da média deve ser **configurável por
  instituição/curso**, pois pode variar entre regulamentos e ao longo dos anos.
- **Documentos de identificação de alunos**: Bilhete de Identidade (BI), Cédula Pessoal,
  Passaporte, Assento de Nascimento — o sistema deve suportar todos.
- **Encarregado de Educação**: figura central angolana (nem sempre é o pai/mãe biológico),
  com responsabilidade legal e financeira sobre o aluno.

## 1.5 Desafios específicos da realidade angolana

Estes desafios moldam directamente as decisões de arquitetura (ver
[08-offline-first-e-sincronizacao.md](08-offline-first-e-sincronizacao.md)):

- **Conectividade instável ou inexistente**: muitas escolas, sobretudo fora de Luanda e
  das capitais provinciais, não têm Internet fixa fiável; dependem de dados móveis
  (Unitel, Movicel, Africell) com cobertura variável.
- **Fornecimento eléctrico intermitente**: quedas de energia frequentes tornam
  indispensável que o sistema local seja resiliente a desligamentos abruptos (integridade
  transacional da base de dados) e que se recomende UPS/nobreak.
- **Dispersão geográfica**: 18 províncias, com realidades de infraestrutura muito
  diferentes entre Luanda e o interior.
- **Custo de dados móveis**: a sincronização deve ser eficiente em banda (deltas, não
  cargas completas) para minimizar custos de dados quando a ligação é por rede móvel.
- **Parque informático heterogéneo e modesto**: computadores antigos, tablets e
  smartphones de gama baixa — o frontend deve ser leve, funcional em navegadores
  desactualizados e não depender de hardware potente.
- **Multiplicidade de meios de pagamento**: transferência bancária, Multicaixa Express,
  numerário — o módulo financeiro deve acomodar registo manual e, no futuro,
  integrações.

## 1.6 Público-alvo

- Instituições de ensino privadas e públicas do Ensino Secundário (I e II Ciclo).
- Redes de escolas com múltiplas unidades (multi-instituição, gerido a partir de um nó
  central).
- Secretarias escolares, direções pedagógicas, direções financeiras/tesourarias,
  departamentos de recursos humanos.
- Encarregados de educação e alunos.
- Público em geral interessado em informação institucional (admissões, contactos,
  comunicados).

## 1.7 Princípios orientadores

1. **Offline-first**: a operação diária da escola nunca deve depender da Internet.
2. **Simplicidade de implantação**: um único servidor local (mini-PC/NUC) deve bastar
   para uma escola de porte médio.
3. **Frontend integrado no Django**: sem SPA (React/Vue/Angular); interatividade obtida
   com Django Templates + HTMX + Alpine.js + CSS server-side, garantindo simplicidade de
   manutenção e menor custo de operação.
4. **Nacionalização e inclusão linguística**: idioma português de Angola como língua
   oficial de trabalho, moeda Kwanza (AOA), calendário e feriados angolanos, estrutura
   curricular do MED — complementado por suporte multilíngue nativo a, pelo menos, 5
   línguas nacionais mais faladas (Umbundu, Kimbundu, Kikongo, Chokwe, Oshikwanyama),
   como preferência pessoal de cada utilizador (ver
   [03-requisitos-nao-funcionais.md §3.7](03-requisitos-nao-funcionais.md)).
5. **Baixo custo total de propriedade**: hardware modesto, licenciamento 100% software
   livre/open source na stack base.
6. **Auditabilidade**: qualquer alteração a notas, matrículas e pagamentos é rastreável
   (quem, quando, o quê).
7. **Extensibilidade controlada**: arquitetura modular (apps Django) que permite adicionar
   funcionalidades (ex.: biblioteca, cantina) sem reescrever o núcleo.

## 1.8 Dentro e fora do escopo

**Dentro do escopo (v1.0):**
- Inscrição e matrícula de alunos.
- Gestão curricular (departamentos, cursos, disciplinas, turmas, horários).
- Avaliação e notas, pautas e boletins.
- Frequência/assiduidade.
- Gestão financeira de propinas/mensalidades e emissão de recibos.
- Gestão de funcionários e recursos humanos por secção.
- Portais: público, aluno, encarregado de educação.
- Área administrativa restrita.
- Sincronização offline/online entre nó local (escola) e nó central (nuvem).
- Relatórios e documentos oficiais (declarações, certificados, pautas).

**Fora do escopo inicial (propostas para fases futuras — ver
[12-plano-de-implementacao.md](12-plano-de-implementacao.md)):**
- Biblioteca escolar.
- Cantina/refeitório.
- Transporte escolar.
- Aplicação móvel nativa (iOS/Android) — o portal responsivo/PWA cobre esta necessidade
  inicialmente.
- Integração directa com sistemas do MED (exportação de relatórios normativos é
  suportada; integração API bidireccional fica para fase posterior, dependente de
  disponibilidade de API oficial).

## 1.9 Marcos macro (Milestones)

O documento original deixava os marcos por preencher (Milestones I e II). Propõe-se:

| Marco | Nome | Conteúdo |
|---|---|---|
| M1 | Fundação | Instituição, utilizadores/perfis, currículo base, inscrição/matrícula, portal público mínimo |
| M2 | Núcleo Pedagógico | Turmas, horários, notas, pautas, frequência |
| M3 | Núcleo Financeiro e RH | Mensalidades/emolumentos, recibos, funcionários por secção |
| M4 | Portais e Comunicação | Portal do aluno e do encarregado, avisos/notificações |
| M5 | Offline/Online Completo | Motor de sincronização multi-nó, modo de contingência sem rede |
| M6 | Rede Multi-Escola | Gestão central de múltiplas instituições, relatórios agregados |

Detalhes de fases, entregáveis e critérios de aceitação em
[12-plano-de-implementacao.md](12-plano-de-implementacao.md).
