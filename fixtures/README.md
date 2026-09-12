# Fixtures

Dados de referência carregados via `python manage.py loaddata <ficheiro>`, usados por
várias apps de negócio (ver docs/10-stack-tecnologica-e-estrutura-projeto.md §10.2):

- `provincias_municipios.json` — províncias e municípios de Angola (usado em moradas de
  alunos, encarregados de educação e instituições).
- `operadoras_moveis.json` — operadoras móveis angolanas (usado na validação/formatação
  de contactos telefónicos).
- `tipos_documento.json` — tipos de documento de identificação aceites (BI, passaporte,
  cédula pessoal, etc.).
- `escala_avaliacao.json` — escala de avaliação oficial (ver
  `docs/legislacao/escala-avaliacao-secundario.md`).

Estes ficheiros ainda não existem — serão criados nas fases do roadmap em que as apps
que os consomem forem implementadas (`enrollment`, `accounts`, `grading`; ver
docs/12-plano-de-implementacao.md), com os dados oficiais correspondentes em vez de
valores de exemplo.
