#!/bin/sh
# A minimal logical (pg_dump) backup, written to the shared `backups` volume --
# see docs/11-implantacao-e-operacoes.md §11.4. Runs *inside the `db`
# container itself* -- issue #166's "backup automático" is instead handled by
# apps.core.services.backup_database(), scheduled daily via Django-Q2
# (apps.core.signals.schedule_automatic_backup), which does the equivalent
# dump from `web`/`qcluster` over the network instead. This script stays as
# the manual, no-Django-required fallback -- run it by hand, or wire it into
# the host's own cron/systemd timer, e.g.:
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
DUMP="${BACKUP_DIR}/fenixschool-${TIMESTAMP}.sql"

mkdir -p "${BACKUP_DIR}"

# Deliberately not `pg_dump ... | gzip > "$DUMP.gz"`: under `/bin/sh` (which on
# both the Debian app image and this Alpine-based postgres image is not bash),
# `set -e` only sees a pipeline's *last* command's exit status -- gzip would
# still exit 0 and "succeed" even if pg_dump failed, silently producing an
# empty/corrupt backup that reports success. Writing the plain dump first
# means a failing pg_dump aborts the script immediately, before gzip ever
# runs.
echo "Backing up ${POSTGRES_DB} to ${DUMP}.gz..."
pg_dump --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" --file "${DUMP}"
gzip "${DUMP}"
echo "Done."
