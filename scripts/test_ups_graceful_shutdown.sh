#!/bin/sh
# Testa scripts/ups_graceful_shutdown.sh (issue #168's "encerramento
# gracioso testado com simulação de bateria baixa") sem precisar de
# hardware de UPS real nem de instalar o NUT.
#
# `upsmon`'s própria decisão de "a bateria está baixa, é hora de encerrar" é
# software de terceiros bem estabelecido (o NUT em si) -- não é isso que
# este teste verifica. O que interessa testar aqui é a *reacção* deste
# projecto a essa decisão, que é inteiramente o comportamento de
# ups_graceful_shutdown.sh: ordem correcta (backup -> stop -> encerrar SO
# só se pedido), e que uma falha no backup nunca impede a paragem da stack
# (nunca vale a pena arriscar corrupção de dados à espera de um backup que
# falhou). Faz isso substituindo `docker`/`shutdown` por stubs numa PATH
# temporária que só registam como foram chamados.
#
# Corrido por `python manage.py test`/pytest? Não -- é um script de
# infra-estrutura do host, fora da app Django (nunca corre dentro de nenhum
# container), por isso o teste é o mesmo tipo de shell script, não pytest.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_UNDER_TEST="${SCRIPT_DIR}/ups_graceful_shutdown.sh"

FAILURES=0

# --- stubs -------------------------------------------------------------

setup_stubs() {
    STUB_DIR="$(mktemp -d)"
    CALL_LOG="${STUB_DIR}/calls.log"
    : > "${CALL_LOG}"

    cat > "${STUB_DIR}/docker" <<EOF
#!/bin/sh
echo "docker \$*" >> "${CALL_LOG}"
if [ "\$4" = "ps" ]; then
    if [ "\${FAKE_WEB_RUNNING:-true}" = "true" ]; then
        echo "web"
    fi
    exit 0
fi
if [ "\$4" = "exec" ]; then
    exit "\${FAKE_BACKUP_EXIT:-0}"
fi
exit 0
EOF
    chmod +x "${STUB_DIR}/docker"

    cat > "${STUB_DIR}/shutdown" <<EOF
#!/bin/sh
echo "shutdown \$*" >> "${CALL_LOG}"
exit 0
EOF
    chmod +x "${STUB_DIR}/shutdown"
}

teardown_stubs() {
    rm -rf "${STUB_DIR}"
}

run_script() {
    PATH="${STUB_DIR}:${PATH}" UPS_COMPOSE_FILE="/fake/compose.yml" \
        "$@" "${SCRIPT_UNDER_TEST}" > /dev/null 2>&1
}

assert_contains() {
    description="$1"
    if grep -qF "$2" "${CALL_LOG}"; then
        echo "ok - ${description}"
    else
        echo "NOT ok - ${description} (esperava '$2' em ${CALL_LOG}: $(cat "${CALL_LOG}"))"
        FAILURES=$((FAILURES + 1))
    fi
}

assert_not_contains() {
    description="$1"
    if grep -qF "$2" "${CALL_LOG}"; then
        echo "NOT ok - ${description} (não devia conter '$2': $(cat "${CALL_LOG}"))"
        FAILURES=$((FAILURES + 1))
    else
        echo "ok - ${description}"
    fi
}

# --- cenário 1: caminho normal, sem pedir encerramento do SO ------------

setup_stubs
FAKE_WEB_RUNNING=true FAKE_BACKUP_EXIT=0 run_script env UPS_SHUTDOWN_HOST=false
assert_contains "faz backup quando 'web' está a correr" "docker compose -f /fake/compose.yml exec -T web python manage.py backup_database"
assert_contains "pára a stack" "docker compose -f /fake/compose.yml stop"
assert_not_contains "não encerra o SO por omissão" "shutdown"
teardown_stubs

# --- cenário 2: backup falha -- a stack tem de parar na mesma -----------

setup_stubs
FAKE_WEB_RUNNING=true FAKE_BACKUP_EXIT=1 run_script env UPS_SHUTDOWN_HOST=false
assert_contains "tenta o backup mesmo que vá falhar" "manage.py backup_database"
assert_contains "pára a stack mesmo com o backup a falhar" "docker compose -f /fake/compose.yml stop"
teardown_stubs

# --- cenário 3: 'web' não está a correr -- salta o backup, pára à mesma -

setup_stubs
FAKE_WEB_RUNNING=false run_script env UPS_SHUTDOWN_HOST=false
assert_not_contains "salta o backup quando 'web' não está a correr" "manage.py backup_database"
assert_contains "pára a stack mesmo sem 'web' a correr" "docker compose -f /fake/compose.yml stop"
teardown_stubs

# --- cenário 4: UPS_SHUTDOWN_HOST=true encerra o SO no final ------------

setup_stubs
FAKE_WEB_RUNNING=true FAKE_BACKUP_EXIT=0 run_script env UPS_SHUTDOWN_HOST=true
assert_contains "encerra o SO quando pedido explicitamente" "shutdown -h now"
teardown_stubs

echo
if [ "${FAILURES}" -eq 0 ]; then
    echo "Todos os testes passaram."
    exit 0
else
    echo "${FAILURES} teste(s) falharam."
    exit 1
fi
