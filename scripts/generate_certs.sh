#!/bin/bash
set -e

CERT_DIR="${1:-./certs}"
DOMAIN="${2:-localhost}"
IP="${3:-127.0.0.1}"

mkdir -p "$CERT_DIR"

echo "Generating self-signed certificate for demo testing..."

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.crt" \
  -subj "/C=US/ST=Demo/L=Demo/O=PrimeVPN/CN=$DOMAIN" \
  -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:$IP"

echo "Certificate generated:"
echo "  Certificate: $CERT_DIR/server.crt"
echo "  Private Key: $CERT_DIR/server.key"
echo ""
echo "For mobile testing:"
echo "1. Install server.crt as a trusted CA on your device"
echo "2. Android: Settings > Security > Install from storage"
echo "3. iOS: AirDrop/email the cert and install via Settings"
echo "4. Configure the Flutter app with --dart-define=API_BASE_URL=https://$IP:443"
