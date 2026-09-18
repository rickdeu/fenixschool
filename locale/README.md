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

Os ficheiros `<code>/LC_MESSAGES/django.po` existem mas ainda **sem nenhuma entrada
traduzida**: nenhum template/string do código está ainda marcado com `{% trans %}`/
`gettext()` (issue #151), por isso `django-admin makemessages` não teria nada para
extrair. À medida que o código for marcado, executar:

```bash
django-admin makemessages -l umb -l kmb -l kon -l cjk -l kua
```

para actualizar estes ficheiros com as strings reais, e `django-admin compilemessages`
para gerar os `.mo` que o Django usa em tempo de execução (issue #150).
