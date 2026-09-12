# 14. Glossário

## Termos de negócio (contexto angolano)

| Termo | Definição |
|---|---|
| **Inscrição** | Acto único e perpétuo de criação de um aluno no sistema, com atribuição de número de aluno. Feito apenas uma vez na vida escolar do aluno na instituição. |
| **Matrícula** | Acto anual que associa um aluno já inscrito a um Curso/Ano Lectivo/Turma. Repetido em cada Ano Lectivo. |
| **Ano Lectivo** | Período anual de actividade escolar (ex. "2026/2027"), com data de início e fim. |
| **Período Lectivo** | Subdivisão do Ano Lectivo (habitualmente Trimestres em Angola). |
| **Ciclo Lectivo** | Agrupamento estrutural do currículo (ex. "1.º Ciclo", "2.º Ciclo"). |
| **Ano Curricular** | Posição do aluno dentro da estrutura do curso (1.º, 2.º, 3.º, 4.º ano do curso), distinto da "classe" administrativa. |
| **Classe** | Designação tradicional angolana do ano de escolaridade (ex. "10.ª classe"). |
| **I Ciclo do Ensino Secundário** | 7.ª à 9.ª classe. |
| **II Ciclo do Ensino Secundário / Ensino Médio** | 10.ª à 13.ª classe, organizado por cursos/áreas de formação. |
| **MAC** | Média de Avaliação Contínua — um dos componentes usados no cálculo da média final do aluno. |
| **Encarregado de Educação** | Pessoa (pai, mãe, tutor ou outro) legalmente responsável pelo aluno perante a instituição; figura central no direito angolano de educação. |
| **BI** | Bilhete de Identidade — documento de identificação nacional angolano. |
| **MED / MINED** | Ministério da Educação da República de Angola. |
| **Propina/Mensalidade** | Valor devido periodicamente pelo aluno à instituição pela frequência escolar. |
| **Emolumento** | Taxa cobrada por serviço específico (ex. emissão de certificado, 2.ª via de documento). |
| **Pauta** | Documento oficial que regista as classificações de uma turma/disciplina/período. |
| **Boletim** | Extracto de notas individual de um aluno. |
| **Multicaixa Express** | Sistema de pagamento electrónico bancário angolano, meio de pagamento comum. |

## Termos técnicos de arquitetura

| Termo | Definição |
|---|---|
| **Nó Local** | Instância do sistema instalada fisicamente na escola, operando de forma autónoma sem depender de Internet. |
| **Nó Central** | Instância na nuvem que agrega dados de múltiplas instituições, hospeda o portal público externo e coordena a sincronização. |
| **Tenant** | Uma instituição, no contexto multi-tenant do Nó Central — todos os dados de negócio têm `instituicao_id`. |
| **Outbox / Changelog** | Tabela que regista cada alteração de negócio como um evento a sincronizar, gravada na mesma transacção da alteração original. |
| **Last-Write-Wins (LWW)** | Estratégia de resolução de conflito em que a alteração com timestamp mais recente prevalece automaticamente — reservada a campos não-críticos. |
| **Soft-delete** | Marcação de um registo como eliminado (`is_deleted=True`) sem remoção física, preservando histórico e integridade de sincronização. |
| **UUID v7** | Identificador único universal ordenável por tempo, usado como chave primária para permitir fusão de dados de múltiplos nós sem colisão. |
| **Sneakernet** | Transferência de dados por meio físico (pen-drive) quando não existe qualquer via de rede disponível. |
| **HTMX** | Biblioteca JavaScript leve que permite actualizar fragmentos de página via atributos HTML, sem necessidade de SPA. |
| **PWA** | Progressive Web App — aplicação web com capacidades de cache offline e instalação, usada nos portais externos. |
| **RBAC** | Role-Based Access Control — modelo de controlo de acesso por perfil/papel. |
