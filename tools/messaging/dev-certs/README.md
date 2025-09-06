Dev TLS Certificates

- Self-signed CA + server + client certificates for local development.
- Replace with real certificates in production.

Usage
- Run `./make-certs.sh` to generate CA and server/client certs into this folder.
- Configure services to use `ca.pem`, `server.pem/server.key`, and `client.pem/client.key`.
