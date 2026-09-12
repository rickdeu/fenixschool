#!/bin/sh
# A minimal logical (pg_dump) backup, written to the shared `backups` volume --
# see docs/11-implantacao-e-operacoes.md §11.4. Run it manually, or wire it
# into the host's own cron/systemd timer, e.g.:
#
#   docker compose -f docker-compose.local-node.yml exec -T db \
#       /usr/local/bin/backup.sh
#
# This deliberately only covers the "daily pg_dump to local disk" row of
# §11.4's backup table. Encryption, rotation/retention, off-site copies and
# the `.fsxsync` contingency export are real, separate pieces of work left to
# a dedicated backups issue -- this script is the plumbing they would build
# on top of, not a replacement for them.
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${BACKUP_DIR}/fenixschool-${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "Backing up ${POSTGRES_DB} to ${DEST}..."
pg_dump --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" | gzip > "${DEST}"
echo "Done."
