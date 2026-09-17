#!/bin/sh
# Generates a self-signed root CA and a server certificate for the local
# node's Nginx (issue #142, docs/09-seguranca-e-privacidade.md §9.3:
# "certificado auto-assinado interno aceitável na LAN da escola... com
# distribuição do certificado raiz aos dispositivos da instituição").
#
# Not needed for the central node, which should use a publicly trusted
# certificate (e.g. Let's Encrypt/certbot) instead -- see
# docs/11-implantacao-e-operacoes.md.
#
# Usage:
#   ./scripts/generate_local_node_tls_cert.sh escola-exemplo.local
#   docker compose -f docker-compose.local-node.yml -f docker-compose.tls.yml up -d
#
# Run this once per installation, before the first `docker compose up` with
# docker-compose.tls.yml layered on top. Re-running it overwrites the
# existing certificate/CA (they are not reused between installations -- see
# the acceptance criterion above).
set -eu

SERVER_NAME="${1:?Usage: $0 <server-name, e.g. escola-exemplo.local>}"
CERT_DIR="${CERT_DIR:-./certs}"
DAYS_VALID="${DAYS_VALID:-3650}"

mkdir -p "${CERT_DIR}"

echo "Generating root CA..."
openssl req -x509 -newkey rsa:4096 -sha256 -days "${DAYS_VALID}" -nodes \
    -keyout "${CERT_DIR}/rootCA.key" \
    -out "${CERT_DIR}/rootCA.pem" \
    -subj "/O=FenixSchool/CN=FenixSchool Local Node Root CA"

echo "Generating server key and certificate signing request for ${SERVER_NAME}..."
openssl req -newkey rsa:2048 -nodes \
    -keyout "${CERT_DIR}/privkey.pem" \
    -out "${CERT_DIR}/server.csr" \
    -subj "/O=FenixSchool/CN=${SERVER_NAME}"

echo "Signing server certificate with the root CA..."
# A plain temp file rather than `<(...)` process substitution: this script
# targets POSIX `/bin/sh` (see scripts/backup.sh), which dash doesn't support.
EXTFILE="$(mktemp)"
printf "subjectAltName=DNS:%s" "${SERVER_NAME}" > "${EXTFILE}"
openssl x509 -req -sha256 -days "${DAYS_VALID}" \
    -in "${CERT_DIR}/server.csr" \
    -CA "${CERT_DIR}/rootCA.pem" \
    -CAkey "${CERT_DIR}/rootCA.key" \
    -CAcreateserial \
    -extfile "${EXTFILE}" \
    -out "${CERT_DIR}/fullchain.pem"

rm -f "${CERT_DIR}/server.csr" "${CERT_DIR}/rootCA.srl" "${EXTFILE}"

cat <<EOF

Done. Files written to ${CERT_DIR}/:
  - rootCA.pem / rootCA.key  (root CA -- keep rootCA.key offline/safe)
  - fullchain.pem / privkey.pem  (server certificate, used by Nginx)

Next step (required -- browsers/devices will otherwise show a certificate
warning): distribute ${CERT_DIR}/rootCA.pem to every device on the
institution's network and install it as a trusted root certificate. This is
a one-time step per device.
EOF
