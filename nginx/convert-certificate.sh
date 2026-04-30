#!/bin/bash
# Convert PFX certificate to nginx-compatible format

set -e

PFX_FILE="$1"
CERT_PASSWORD="$2"

if [ -z "$PFX_FILE" ] || [ -z "$CERT_PASSWORD" ]; then
    echo "Usage: $0 <pfx-file> <password>"
    echo "Example: $0 certificate.pfx mypassword"
    exit 1
fi

if [ ! -f "$PFX_FILE" ]; then
    echo "❌ Error: PFX file '$PFX_FILE' not found!"
    exit 1
fi

echo "🔒 Converting PFX certificate to nginx format..."

# Extract private key
echo "📤 Extracting private key..."
openssl pkcs12 -in "$PFX_FILE" -nocerts -out temp_private.key -passin pass:"$CERT_PASSWORD" -passout pass:temp123

# Remove passphrase from private key
echo "🔓 Removing passphrase from private key..."
openssl rsa -in temp_private.key -out private.key -passin pass:temp123

# Extract certificate
echo "📜 Extracting certificate..."
openssl pkcs12 -in "$PFX_FILE" -clcerts -nokeys -out certificate.crt -passin pass:"$CERT_PASSWORD"

# Extract CA chain (if present)
echo "🔗 Extracting certificate chain..."
openssl pkcs12 -in "$PFX_FILE" -cacerts -nokeys -out ca_chain.crt -passin pass:"$CERT_PASSWORD" 2>/dev/null || echo "No CA chain found"

# Create fullchain certificate (cert + intermediate + root)
if [ -f "ca_chain.crt" ] && [ -s "ca_chain.crt" ]; then
    echo "🔗 Creating full certificate chain..."
    cat certificate.crt ca_chain.crt > fullchain.crt
else
    echo "📋 Using certificate without chain..."
    cp certificate.crt fullchain.crt
fi

# Clean up temporary files
rm -f temp_private.key ca_chain.crt

# Move files to nginx SSL directory
echo "📁 Moving certificates to nginx SSL directory..."
sudo mv private.key /etc/nginx/ssl/
sudo mv certificate.crt /etc/nginx/ssl/
sudo mv fullchain.crt /etc/nginx/ssl/

# Set proper permissions
sudo chmod 600 /etc/nginx/ssl/private.key
sudo chmod 644 /etc/nginx/ssl/certificate.crt
sudo chmod 644 /etc/nginx/ssl/fullchain.crt

# Set ownership
sudo chown root:root /etc/nginx/ssl/*

echo "✅ Certificate conversion complete!"
echo "📁 Files created:"
echo "   - /etc/nginx/ssl/private.key (Private key)"
echo "   - /etc/nginx/ssl/certificate.crt (Certificate)"
echo "   - /etc/nginx/ssl/fullchain.crt (Full certificate chain)"
echo ""
echo "🔒 Certificate details:"
openssl x509 -in /etc/nginx/ssl/certificate.crt -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:)"