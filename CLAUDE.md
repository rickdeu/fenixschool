# Instruções do projeto FenixSchool

## Scripts

Todo o script utilizado neste projeto (Python, bash, migrações de dados, scripts de
automação, scripts pontuais para tarefas administrativas como criação de issues/labels
no GitHub, etc.) deve ficar guardado dentro da pasta `scripts/` na raiz do repositório —
nunca em `/tmp` ou noutra pasta temporária fora do projeto.

- Cada script deve ter um nome descritivo do que faz (ex.: `create_github_tasks.py`,
  `backup_local_node.sh`).
- Scripts de uso único ou administrativos (não fazem parte da aplicação em si) também
  devem ficar aqui, não em `apps/` nem dispersos na raiz.
- Isto garante que qualquer script já escrito/executado neste projeto fica rastreável no
  histórico do repositório e reutilizável no futuro, em vez de se perder em ficheiros
  temporários.
