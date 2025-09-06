#!/usr/bin/env bash
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
cd "$DIR"
openssl req -x509 -nodes -new -sha256 -days 3650 -newkey rsa:2048 \
  -subj "/CN=dev-ca" -keyout ca.key -out ca.pem
openssl req -new -nodes -newkey rsa:2048 -keyout server.key -out server.csr -subj "/CN=localhost"
openssl x509 -req -in server.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out server.pem -days 365 -sha256
openssl req -new -nodes -newkey rsa:2048 -keyout client.key -out client.csr -subj "/CN=dev-client"
openssl x509 -req -in client.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out client.pem -days 365 -sha256
echo "Generated CA, server, and client certs in $(pwd)"
