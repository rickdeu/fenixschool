# Catálogos de tradução

Estrutura de catálogos para as 5 línguas nacionais angolanas opcionais (issue #148,
RF-I18N-01, docs/10-stack-tecnologica-e-estrutura-projeto.md §10.4.1) — português é a
língua de origem do código-fonte (todas as `verbose_name`/labels já estão em português),
por isso não tem catálogo próprio aqui.

| Código | Língua |
|---|---|
| `umb` | Umbundu |
| `kmb` | Kimbundu |
| `kon` | Kikongo |
| `cjk` | Chokwe |
| `kua` | Oshikwanyama |

Todo o texto fixo de interface marcado até agora (issue #151: ecrãs de login, assistente
de instalação, Inscrição, Matrícula) já foi extraído para estes ficheiros — mas **ainda
sem nenhuma entrada traduzida** (todos os `msgstr` estão vazios). À medida que mais
templates/strings forem marcados com `{% translate %}`/`{% blocktranslate %}`/
`gettext_lazy()`, repetir o processo abaixo.

## 1. Extrair strings (`makemessages`)

Requer as ferramentas `gettext` (não incluídas na imagem base da aplicação — apenas
necessárias em ambiente de desenvolvimento/tradução, não em produção):

```bash
# Dentro do container da app (ou em qualquer ambiente com gettext instalado):
apt-get install -y gettext   # já testado dentro do container `web` do Nó Local
python manage.py makemessages -l umb -l kmb -l kon -l cjk -l kua --no-obsolete
```

Testado em 2026-09-18 contra o estado actual do código: extraiu correctamente todas as
strings marcadas de `apps/accounts/forms.py` (labels/mensagens de erro do login) e de
todos os templates de `accounts`, `core` e `enrollment` construídos até essa data.

## 2. Traduzir

Cada ficheiro `<code>/LC_MESSAGES/django.po` é um ficheiro de texto simples (formato
gettext) — cada entrada tem um `msgid` (o texto original em português) e um `msgstr`
(a tradução, inicialmente vazio). Processo incremental recomendado:

1. Atribuir cada língua a um colaborador/falante nativo (ou parceria com o Instituto de
   Línguas Nacionais — ILN).
2. O colaborador edita apenas os campos `msgstr` do seu ficheiro (nunca os `msgid`,
   que reflectem o texto-fonte em português) — com um editor de texto simples ou uma
   ferramenta de tradução gettext (ex. Poedit).
3. Submeter as alterações via Pull Request, como qualquer outra alteração ao código.
4. Rever a tradução (idealmente por um segundo falante nativo) antes de mesclar.
5. Não é necessário traduzir tudo de uma vez — uma tradução parcial é válida: o Django
   usa o texto em português (`msgid`) sempre que não existir `msgstr` para a entrada.

## 3. Compilar (`compilemessages`)

```bash
python manage.py compilemessages
```

Gera os ficheiros `.mo` binários que o Django lê em tempo de execução (formato
optimizado, não editável directamente). Testado em 2026-09-18, sem erros. Os `.mo` não
são commitados no repositório (são um artefacto derivado dos `.po`, tal como
`staticfiles/`) — deverão ser gerados no processo de build/deploy assim que existirem
traduções reais a compilar; nenhum passo de deploy os gera automaticamente ainda,
porque nenhuma tradução real existe neste momento.
