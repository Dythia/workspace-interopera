#!/bin/bash

# Script to decrypt files in vault directory and store/replace them in .secret directory

# Prompt for password
echo "Enter decryption password:"
read -s PASSWORD

# Check if password is empty
if [ -z "$PASSWORD" ]; then
    echo "Error: Password cannot be empty"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRET_DIR="$SCRIPT_DIR/.secret"
VAULT_DIR="$SCRIPT_DIR/vault"

# Files to decrypt to root directory instead of .secret
ROOT_FILES=(
    "Dockerfile.be.dev"
    "Dockerfile.fe.dev"
)

# Check if vault directory exists
if [ ! -d "$VAULT_DIR" ]; then
    echo "Error: Vault directory does not exist"
    exit 1
fi

# Process each .enc file in vault directory
for file in "$VAULT_DIR"/*.enc; do
    if [ -f "$file" ]; then
        filename=$(basename "$file" .enc)
        
        # Check if this is a root file that should be decrypted to root directory
        if [[ " ${ROOT_FILES[@]} " =~ " ${filename} " ]]; then
            decrypted_file="$SCRIPT_DIR/$filename"
        else
            decrypted_file="$SECRET_DIR/$filename"
        fi
        
        echo "Decrypting $filename..."
        
        # Decrypt the file using openssl
        echo "$PASSWORD" | openssl enc -d -aes-256-cbc -salt -pbkdf2 -in "$file" -out "$decrypted_file" -pass stdin
        
        if [ $? -eq 0 ]; then
            echo "Successfully decrypted $filename to $decrypted_file"
        else
            echo "Error decrypting $filename (wrong password?)"
        fi
    fi
done

echo "Decryption complete. Decrypted files are stored in $SECRET_DIR and root directory (for Dockerfiles)"
