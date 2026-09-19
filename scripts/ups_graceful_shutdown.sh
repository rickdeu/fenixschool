#!/bin/sh
# Encerramento gracioso do Nó Local ao atingir um limiar de bateria da UPS
# (issue #168, docs/11-implantacao-e-operacoes.md §11.1) -- evita corrupção
# de dados num corte de energia prolongado, mesmo com UPS.
#
# Integração com NUT (Network UPS Tools), o idiomático "ou equivalente" da
# própria issue: `upsmon` já sabe falar com o hardware da UPS (via `upsd`) e
# decidir *quando* accionar um encerramento forçado (FSD) -- este script não
# reimplementa esse polling. É antes o `SHUTDOWNCMD` que `upsmon` invoca
# nesse momento (ver /etc/nut/upsmon.conf abaixo), cujo único trabalho é
# parar a stack Docker de forma limpa (incl. backup final e paragem
# ordenada do Postgres) *antes* do encerramento do próprio sistema
# operativo continuar.
#
# Instalação (no host do Nó Local, não dentro de nenhum container):
#   1. `apt install nut` (driver real da UPS: `usbhid-ups` é o mais comum).
#   2. /etc/nut/ups.conf:
#        [ups_local]
#            driver = usbhid-ups
#            port = auto
#   3. /etc/nut/upsmon.conf:
#        MONITOR ups_local@localhost 1 upsmon <password> master
#        SHUTDOWNCMD "/opt/fenixschool/scripts/ups_graceful_shutdown.sh"
#        FINALDELAY 30
#   4. `systemctl enable --now nut-server nut-monitor`.
#
# Teste sem hardware real (o "simulação de bateria baixa" do critério de
# aceitação desta issue): NUT tem um driver `dummy-ups` para isto -- ver
# scripts/test_ups_graceful_shutdown.sh, que stubba o comando `upsc`
# directamente (mais simples e mais rápido do que correr `upsd`/`upsmon`/
# `dummy-ups` de verdade só para testar a lógica de decisão deste script).
set -eu

COMPOSE_FILE="${UPS_COMPOSE_FILE:-/opt/fenixschool/docker-compose.local-node.yml}"
SHUTDOWN_HOST="${UPS_SHUTDOWN_HOST:-false}"

log() {
    echo "[ups_graceful_shutdown] $(date -Iseconds) $*"
}

log "Bateria da UPS abaixo do limiar -- a iniciar encerramento gracioso."

# Backup final antes de parar tudo -- `apps.core.services.backup_database()`
# via `manage.py backup_database` (issue #166), não o `scripts/backup.sh`
# directo ao container `db`: com a stack prestes a parar, correr através de
# `web` (que já tem as credenciais/settings Django resolvidas) é mais
# simples do que montar os mesmos argumentos aqui outra vez.
if docker compose -f "${COMPOSE_FILE}" ps --status running --services 2>/dev/null | grep -qx web; then
    log "A criar backup final..."
    if ! docker compose -f "${COMPOSE_FILE}" exec -T web python manage.py backup_database; then
        log "AVISO: backup final falhou -- a continuar com o encerramento na mesma (nunca vale a pena arriscar corrupção de dados por um backup em falta)."
    fi
else
    log "Serviço 'web' não está a correr -- a saltar o backup final."
fi

log "A parar a stack Docker (docker compose stop)..."
# `stop`, não `down`: `down` também remove a rede/containers -- desnecessário
# aqui e mais lento a reverter no arranque seguinte. `stop` já é suficiente
# para um encerramento limpo do Postgres (SIGTERM, não SIGKILL).
docker compose -f "${COMPOSE_FILE}" stop

log "Stack parada."

if [ "${SHUTDOWN_HOST}" = "true" ]; then
    log "UPS_SHUTDOWN_HOST=true -- a encerrar o sistema operativo."
    exec shutdown -h now
fi

log "UPS_SHUTDOWN_HOST não é 'true' -- a stack ficou parada, mas o sistema operativo não foi encerrado (deixa-se isso a cargo do próprio upsmon/FSD, que corre este script como SHUTDOWNCMD e depois decide o resto)."
