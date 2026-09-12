# 13. Testes e Qualidade

## 13.1 Estratégia geral

| Nível | Ferramenta | Foco |
|---|---|---|
| Unitário | `pytest` + `pytest-django` | `services.py` de cada app (regras de negócio isoladas) |
| Integração | `pytest-django` + `Client` do Django | Fluxos completos (inscrição→matrícula, lançamento→fecho de pauta, matrícula→plano de mensalidades→pagamento) |
| Sincronização | Suite dedicada `tests/sync_partition/` com múltiplos containers | Ver 13.3 |
| Interface (fumo) | Playwright (opcional, ecrãs críticos) | Fluxos de utilizador final nos portais |
| Carga leve | `locust` (opcional, antes de escala multi-escola) | Nó Central sob concorrência de várias instituições |
| Estático | `ruff`, `mypy` (opcional) | RNF-MAN-01 |
| Segurança de dependências | `pip-audit` | Vulnerabilidades conhecidas em pacotes |

## 13.2 Cobertura mínima

- Núcleo de negócio (`enrollment`, `grading`, `finance`, `sync`): **≥ 70%** (RNF-MAN-03).
- Restantes apps: sem limite rígido, mas todo `service` com lógica condicional deve ter
  pelo menos um teste de caminho feliz e um de caminho de erro.

## 13.3 Testes de sincronização (críticos ao projeto)

Dado que o requisito offline-first é estruturante, esta suite recebe atenção
desproporcional face ao tamanho do módulo:

1. **Teste de partição simples**: dois containers Django (simulando Nó Local e Nó
   Central) com rede Docker cortada a meio de uma sincronização; validar retomada
   correcta sem duplicação.
2. **Teste de idempotência**: reenviar o mesmo lote de `RegistoAlteracao` duas vezes;
   segunda aplicação deve ser no-op.
3. **Teste de conflito não-crítico**: mesma entidade, campos diferentes alterados em
   ambos os lados; validar *merge* automático correcto.
4. **Teste de conflito crítico**: mesma Nota/Pagamento/Matrícula alterada de forma
   divergente; validar que **nunca** é aplicado automaticamente e que aparece na fila de
   `Conflito`.
5. **Teste de sneakernet**: gerar pacote `.fsxsync`, importar noutro nó, validar
   aplicação idêntica ao fluxo automático.
6. **Teste de resiliência a corte de energia**: `SIGKILL` no processo Django/Postgres a
   meio de uma transacção; validar, ao reiniciar, que não há dados parciais.
7. **Teste de carga de sincronização**: volume de um trimestre real (≈3.000 alunos × N
   notas/faltas) sincronizado sob latência/perda de pacotes simulada (ex. `tc netem`).

## 13.4 Definição de Pronto (Definition of Done)

Uma funcionalidade só é considerada concluída quando:
- Testes automatizados cobrem o(s) `service(s)` envolvido(s).
- Alterações de modelo geram entradas correctas no changelog de sincronização (quando
  aplicável) — validado por teste, não apenas por inspecção.
- Interface funciona correctamente em ecrã de telemóvel (para módulos de portal
  externo).
- Textos e mensagens de erro em português claro, sem jargão técnico exposto ao
  utilizador final.
- Documentação técnica actualizada (este pacote `docs/`) quando a alteração afecta
  modelo de dados, arquitetura ou requisitos.

## 13.5 Pipeline de CI (referência)

```yaml
# .github/workflows/ci.yml (esboço de referência)
name: CI
on: [push, pull_request]
jobs:
  qualidade:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
    steps:
      - uses: actions/checkout@v4
      - name: Instalar dependências
        run: pip install -r requirements/dev.txt
      - name: Lint
        run: ruff check .
      - name: Auditoria de dependências
        run: pip-audit
      - name: Testes unitários e de integração
        run: pytest --cov=apps --cov-fail-under=70
      - name: Testes de sincronização (partição simulada)
        run: pytest tests/sync_partition -m sync
      - name: Build da imagem Docker
        run: docker build -t fenixschool:ci .
```

## 13.6 Testes com utilizadores reais (usabilidade)

Antes de cada marco (M1–M6, ver
[12-plano-de-implementacao.md](12-plano-de-implementacao.md)) ser considerado fechado,
realizar uma sessão de utilização assistida com pessoal real da escola piloto (secretaria,
docente, encarregado de educação), medindo:
- Tempo para completar a tarefa-chave do marco sem assistência.
- Número de erros/confusões observadas.
- Satisfação subjectiva (escala simples 1–5).

Resultados alimentam ajustes de UX antes de avançar para o marco seguinte.
