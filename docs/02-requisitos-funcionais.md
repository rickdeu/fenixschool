# 02. Requisitos Funcionais

Convenção de identificação: `RF-<MÓDULO>-<NÚMERO>`. Prioridade em escala MoSCoW
(Must/Should/Could/Won't, nesta fase). Cada requisito é rastreável até um módulo em
[06-modulos-e-funcionalidades.md](06-modulos-e-funcionalidades.md) e até entidades em
[05-modelo-de-dados.md](05-modelo-de-dados.md).

## 2.1 Gestão da Instituição (INST)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-INST-01 | O sistema deve permitir registar os dados da instituição: nome, NIF, endereço completo (província, município, distrito/comuna, bairro, rua, casa), contactos (telefone fixo, Unitel, Movicel/Africell, email), logótipo, website. | Must |
| RF-INST-02 | O sistema deve suportar múltiplas instituições no mesmo nó central (rede de escolas), cada uma com os seus dados isolados. | Should |
| RF-INST-03 | O sistema deve permitir configurar o(s) Ano(s) Lectivo(s), com datas de início/fim, e definir qual é o ano lectivo corrente. | Must |
| RF-INST-04 | O sistema deve permitir configurar os Períodos Lectivos (trimestres/semestres) dentro de um Ano Lectivo, com datas. | Must |
| RF-INST-05 | O sistema deve permitir configurar Ciclos Lectivos (ex.: 1.º Ciclo, 2.º Ciclo) e a sua relação com os cursos. | Must |
| RF-INST-06 | O sistema deve permitir parametrizar a fórmula de cálculo da média final por curso/disciplina/ano lectivo (MAC, PT, Exame — pesos configuráveis). | Must |
| RF-INST-07 | O sistema deve permitir configurar feriados e dias não lectivos angolanos (nacionais e provinciais) para efeitos de calendário e frequência. | Should |
| RF-INST-08 | O sistema deve permitir configurar tabelas de preços (propinas, emolumentos, taxas de matrícula/inscrição, multas por atraso) por ano lectivo e por curso/classe. | Must |

## 2.2 Gestão Curricular (CURR)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-CURR-01 | O sistema deve permitir gerir Departamentos (entidade responsável pelas disciplinas de um curso). | Must |
| RF-CURR-02 | O sistema deve permitir gerir Cursos, com código MED, nome, abreviatura, departamento, data de criação. | Must |
| RF-CURR-03 | O sistema deve permitir gerir Disciplinas associadas a um curso e ano curricular, com tipo (obrigatória/opcional), ciclo e período. | Must |
| RF-CURR-04 | O sistema deve permitir gerir Anos Curriculares (1.º ao 4.º ano do curso, por exemplo) independentemente da "classe" administrativa (10.ª, 11.ª, 12.ª, 13.ª classe). | Must |
| RF-CURR-05 | O sistema deve permitir gerir Turmas: código, designação, ano lectivo, período, número máximo de inscritos, curso, ano curricular. O valor por omissão de lotação deve reflectir os limites legais do Decreto Presidencial 162/23 (36 alunos, até 45 nalgumas regiões, 26 em turmas inclusivas — ver [legislação](legislacao/README.md)), mantendo-se configurável por instituição. | Must |
| RF-CURR-06 | O sistema deve permitir gerir Horários por turma: dia da semana, hora de início/fim, regime (teórica/prática), sala, docente, disciplina — com deteção de conflitos (mesmo docente/sala/turma sobrepostos). | Must |
| RF-CURR-07 | O sistema deve permitir gerir Salas e a sua capacidade. | Should |

## 2.3 Inscrição e Matrícula (MAT)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-MAT-01 | O sistema deve distinguir claramente **Inscrição** (criação única e perpétua do aluno, com atribuição de número de aluno automático e sequencial) de **Matrícula** (associação do aluno a um curso/ano/turma num Ano Lectivo específico, repetida anualmente). | Must |
| RF-MAT-02 | O acto de Inscrição deve capturar: nome, sobrenome, data de nascimento, género, foto, documento de identificação (BI/Cédula/Passaporte/Assento de Nascimento) com número, endereço (província, município, distrito, bairro, rua, n.º de casa), profissão (se aplicável), contactos (telefone móvel/fixo, email), e pelo menos um Encarregado de Educação vinculado. | Must |
| RF-MAT-03 | O sistema deve impedir duplicação de inscrição pelo número de documento de identificação, alertando o operador em caso de correspondência. | Must |
| RF-MAT-04 | O sistema deve permitir localizar um aluno já inscrito por número de aluno, número de documento ou nome, para efeitos de matrícula. | Must |
| RF-MAT-05 | O acto de Matrícula deve capturar: curso, ano lectivo, turma, ciclo lectivo, ano curricular, data da matrícula, estado da matrícula (pendente/activa/anulada/transferida/concluída), tipo e número de documento apresentado, funcionário responsável, observações. | Must |
| RF-MAT-06 | O sistema deve emitir comprovativo de matrícula imprimível (PDF) imediatamente após confirmação ("Guardar e Imprimir"). | Must |
| RF-MAT-07 | O sistema deve validar que o número de alunos matriculados numa turma não excede o número máximo de inscritos definido. | Must |
| RF-MAT-08 | O sistema deve suportar transferência de aluno entre turmas, cursos ou mesmo instituições (transferência externa), preservando o histórico. | Should |
| RF-MAT-09 | O sistema deve suportar matrícula de aluno repetente (retenção), vinculando ao histórico escolar anterior. | Must |
| RF-MAT-10 | O sistema deve permitir o registo e gestão de Candidatos (pré-inscrição/candidatura a uma vaga) antes da inscrição efectiva, com processo de admissão. | Should |
| RF-MAT-11 | O sistema deve permitir associar múltiplos Encarregados de Educação a um aluno (ex.: pai e mãe), com indicação do encarregado principal para efeitos de comunicação e financeiro. | Must |
| RF-MAT-12 | O sistema deve permitir a um Encarregado de Educação estar associado a múltiplos alunos (irmãos), com um único login de acesso ao portal. | Must |

## 2.4 Avaliação e Notas (AVAL)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-AVAL-01 | O sistema deve permitir o lançamento de notas por docente, por disciplina, turma, período lectivo e tipo de avaliação (ex.: MAC, Prova Trimestral, Exame). | Must |
| RF-AVAL-02 | O sistema deve calcular automaticamente a média/classificação final segundo a fórmula parametrizada (ver RF-INST-06), permitindo ajuste manual justificado quando necessário. | Must |
| RF-AVAL-03 | O sistema deve validar que a nota lançada está dentro da escala 0–20 (ou escala configurável) e apresentar o nível qualitativo correspondente (Excelente/Bom/Suficiente/Insuficiente/Mau), conforme o Decreto Executivo 106/26 — ver [escala oficial](legislacao/escala-avaliacao-secundario.md). | Must |
| RF-AVAL-04 | O sistema deve permitir "fechar"/homologar uma pauta de período, impedindo alterações posteriores sem autorização de um perfil superior (Direção Pedagógica), com registo de auditoria. | Must |
| RF-AVAL-05 | O sistema deve gerar Pautas por turma/disciplina/período, e Boletins/Extractos de notas por aluno. | Must |
| RF-AVAL-06 | O sistema deve suportar avaliação de recurso/recuperação e exame especial, quando aplicável, com impacto no cálculo da situação final (aprovado/reprovado/em recurso). | Should |
| RF-AVAL-07 | O sistema deve calcular automaticamente a situação final do aluno no ano lectivo (aprovado, reprovado, com disciplinas em atraso) com base nas médias de todas as disciplinas do ano curricular. | Must |
| RF-AVAL-08 | O sistema deve manter o histórico escolar completo do aluno (todas as notas, todos os anos lectivos), consultável mesmo após transferência ou conclusão. | Must |

## 2.5 Frequência / Assiduidade (FREQ)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FREQ-01 | O sistema deve permitir ao docente registar presenças/faltas por aula (data, disciplina, turma). | Must |
| RF-FREQ-02 | O sistema deve permitir o registo de justificação de faltas, com documento anexo opcional. | Should |
| RF-FREQ-03 | O sistema deve calcular a percentagem de assiduidade do aluno por disciplina/período/ano lectivo, e alertar quando ultrapassa o limite de faltas permitido (parametrizável; valor legal por omissão: 3× a carga horária semanal, conforme Decreto Presidencial 162/23 — ver [legislação](legislacao/README.md)) que impede aprovação por faltas. | Must |
| RF-FREQ-04 | O sistema deve permitir consulta de mapa de faltas por turma, por docente e por encarregado de educação (do seu educando). | Should |

## 2.6 Financeiro (FIN)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FIN-01 | O sistema deve permitir configurar tabelas de propinas/mensalidades e emolumentos (taxa de inscrição, matrícula, certificado, 2.ª via de documentos) por curso/classe/ano lectivo. | Must |
| RF-FIN-02 | O sistema deve gerar automaticamente o plano de mensalidades do aluno ao ser matriculado, respeitando o calendário do ano lectivo. | Must |
| RF-FIN-03 | O sistema deve permitir o registo de pagamentos (mensalidade, emolumentos), incluindo valor pago, mora/juro por atraso (configurável), meio de pagamento (numerário, transferência, Multicaixa Express), data e funcionário responsável. | Must |
| RF-FIN-04 | O sistema deve emitir recibo de pagamento imprimível/PDF, com numeração sequencial e dados fiscais da instituição. | Must |
| RF-FIN-05 | O sistema deve apresentar o extracto financeiro do aluno (dívidas, pagamentos, saldo) a funcionários autorizados e ao encarregado de educação no seu portal. | Must |
| RF-FIN-06 | O sistema deve permitir bloquear a emissão de certos documentos (ex.: certificado, declaração) quando existirem dívidas em aberto, de forma configurável pela instituição. | Should |
| RF-FIN-07 | O sistema deve gerar relatórios financeiros agregados: receita por período, inadimplência por turma/curso, projeção de receita. | Should |
| RF-FIN-08 | O sistema deve suportar descontos e bolsas (percentuais ou fixos) por aluno, com justificação e aprovação. | Could |

## 2.7 Recursos Humanos / Funcionários (RH)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-RH-01 | O sistema deve permitir o registo de Funcionários com dados pessoais, documento de identificação, contactos, secção/departamento funcional (Direção, Secretaria, Financeiro/Tesouraria, Pedagógico, Recursos Humanos, Biblioteca, TI, Apoio/Manutenção), cargo e categoria profissional. | Must |
| RF-RH-02 | O sistema deve permitir associar Docentes a Disciplinas e Turmas (via Horário), controlando carga horária. | Must |
| RF-RH-03 | O sistema deve permitir gerir contratos de trabalho (tipo, data de início/fim, vínculo), sem substituir um sistema de folha de pagamento completo (fora do escopo v1). | Should |
| RF-RH-04 | O sistema deve permitir controlar o estado do funcionário (activo/inactivo/licença/rescisão) e reflectir isso no acesso ao sistema. | Must |
| RF-RH-05 | Cada secção (Secretaria, Financeiro, Pedagógico, RH, Direção) deve poder gerir apenas os seus próprios funcionários e permissões, sob supervisão do administrador da instituição. | Should |

## 2.8 Portal Público (PUB)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-PUB-01 | O sistema deve disponibilizar um sítio público institucional com: apresentação da escola, cursos oferecidos, contactos, localização, horário de atendimento. | Must |
| RF-PUB-02 | O sistema deve publicar comunicados/notícias institucionais (ex.: prazos de matrícula, eventos, calendário escolar) visíveis sem autenticação. | Must |
| RF-PUB-03 | O sistema deve disponibilizar um formulário de pré-candidatura/contacto para o público em geral. | Should |
| RF-PUB-04 | O sistema deve permitir consulta pública de resultados de exames/pautas quando a instituição optar por publicá-los (com dados minimizados, ex.: por número de aluno, não por nome completo). | Could |

## 2.9 Portal do Aluno (ALU)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-ALU-01 | O aluno (ou o encarregado em seu nome, consoante idade/política da instituição) deve poder consultar: dados de matrícula, horário de aulas, notas/pautas, situação de frequência. | Must |
| RF-ALU-02 | O aluno deve poder consultar o seu extracto financeiro (mensalidades pagas/pendentes). | Should |
| RF-ALU-03 | O aluno deve receber comunicados/avisos dirigidos à sua turma/curso/instituição. | Should |
| RF-ALU-04 | O portal do aluno deve funcionar em modo leitura offline com últimos dados sincronizados (PWA com cache), sinalizando claramente quando os dados podem estar desactualizados. | Should |

## 2.10 Portal do Encarregado de Educação (ENC)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-ENC-01 | O encarregado deve poder consultar, para cada educando associado: notas, frequência, situação financeira, comunicados. | Must |
| RF-ENC-02 | O encarregado deve poder efectuar/registar pedidos (ex.: justificação de falta, pedido de declaração) através do portal, mesmo que o processamento final seja manual pela secretaria. | Should |
| RF-ENC-03 | O encarregado deve poder actualizar os seus próprios dados de contacto (telefone, email, endereço). | Must |
| RF-ENC-04 | O sistema deve notificar o encarregado (SMS/email/notificação no portal) sobre eventos relevantes: lançamento de notas, mensalidade em atraso, comunicados importantes — com fila de envio tolerante a falhas de conectividade. | Should |

## 2.11 Área Administrativa Restrita (ADM)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-ADM-01 | O sistema deve fornecer uma área de administração restrita para gestão de utilizadores, perfis e permissões granulares por módulo. | Must |
| RF-ADM-02 | O sistema deve permitir configurar parâmetros globais da instituição (ver secção 2.1). | Must |
| RF-ADM-03 | O sistema deve disponibilizar um painel de auditoria: quem alterou o quê e quando (notas, matrículas, pagamentos, utilizadores). | Must |
| RF-ADM-04 | O sistema deve disponibilizar um painel de estado de sincronização (ver [08-offline-first-e-sincronizacao.md](08-offline-first-e-sincronizacao.md)): último sync bem-sucedido, pendências, conflitos por resolver. | Must |
| RF-ADM-05 | O sistema deve permitir exportação de dados (backup manual, exportações para o MED) em formatos abertos (CSV/JSON/PDF). | Must |
| RF-ADM-06 | O sistema deve permitir a um Super Administrador (nível rede) gerir múltiplas instituições a partir do nó central. | Should |

## 2.12 Relatórios e Documentos Oficiais (REL)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-REL-01 | O sistema deve emitir Declarações (de matrícula, de frequência, de conclusão) em PDF com modelo configurável por instituição. | Must |
| RF-REL-02 | O sistema deve emitir Certificados de conclusão de curso/classe. | Must |
| RF-REL-03 | O sistema deve emitir Pautas oficiais (por turma/disciplina/período/ano). | Must |
| RF-REL-04 | O sistema deve emitir Boletins de notas por aluno/período. | Must |
| RF-REL-05 | O sistema deve emitir relatórios estatísticos (taxa de aprovação, taxa de abandono, mapa de inadimplência) para apoio à decisão da Direção. | Should |
| RF-REL-06 | Todos os documentos oficiais devem incluir numeração/série única, data/hora de emissão e identificação do funcionário emissor, para efeitos de auditoria. | Must |

## 2.13 Sincronização Offline/Online (SYNC)

Ver aprofundamento completo em
[08-offline-first-e-sincronizacao.md](08-offline-first-e-sincronizacao.md). Requisitos
funcionais de topo:

| ID | Requisito | Prioridade |
|---|---|---|
| RF-SYNC-01 | O sistema deve operar de forma totalmente funcional num nó local (na escola) sem qualquer ligação à Internet, para todas as operações do dia-a-dia. | Must |
| RF-SYNC-02 | O sistema deve sincronizar automaticamente as alterações locais com o nó central assim que a conectividade for restabelecida, sem intervenção manual. | Must |
| RF-SYNC-03 | O sistema não deve perder dados em caso de: falha de energia a meio de uma operação, encerramento abrupto, ou perda de conectividade a meio de uma sincronização. | Must |
| RF-SYNC-04 | O sistema deve detectar e sinalizar conflitos de sincronização (ex.: o mesmo registo alterado offline em dois locais) e oferecer um mecanismo de resolução (automático quando seguro, manual quando crítico). | Must |
| RF-SYNC-05 | O sistema deve permitir sincronização alternativa "por transporte físico" (exportação/importação de pacote cifrado via pen-drive) quando não existir qualquer via de rede disponível por período prolongado. | Should |

## 2.14 Multilinguismo (I18N)

Ver aprofundamento em
[03-requisitos-nao-funcionais.md §3.7](03-requisitos-nao-funcionais.md) e
[10-stack-tecnologica-e-estrutura-projeto.md §10.4](10-stack-tecnologica-e-estrutura-projeto.md).

| ID | Requisito | Prioridade |
|---|---|---|
| RF-I18N-01 | O sistema deve disponibilizar a interface em português (idioma por omissão) e em, pelo menos, 5 línguas nacionais angolanas: Umbundu, Kimbundu, Kikongo, Chokwe e Oshikwanyama. | Must |
| RF-I18N-02 | Cada utilizador (funcionário, aluno, encarregado de educação) deve poder escolher e alterar o seu próprio idioma de interface a qualquer momento, de forma independente dos restantes utilizadores da mesma instituição. | Must |
| RF-I18N-03 | Documentos oficiais emitidos pelo sistema (certificados, declarações, pautas, recibos) mantêm-se sempre em português, independentemente do idioma de interface do utilizador que os solicita, por razão de validade legal/administrativa. | Must |
| RF-I18N-04 | O sistema deve permitir cobertura de tradução incremental (lançar com um subconjunto de ecrãs traduzidos por língua e completar progressivamente), sem que isso bloqueie o uso do sistema nas restantes línguas ainda parcialmente traduzidas (esses ecrãs surgem em português como *fallback*). | Should |
