#!/bin/bash

# Script to encrypt files in .secret directory and store encrypted versions in vault directory

# Create vault directory if it doesn't exist
mkdir -p vault

# Prompt for password
echo "Enter encryption password:"
read -s PASSWORD

# Check if password is empty
if [ -z "$PASSWORD" ]; then
    echo "Error: Password cannot be empty"
    exit 1
fi

# Confirm password
echo "Confirm password:"
read -s CONFIRM_PASSWORD

if [ "$PASSWORD" != "$CONFIRM_PASSWORD" ]; then
    echo "Error: Passwords do not match"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRET_DIR="$SCRIPT_DIR/.secret"
VAULT_DIR="$SCRIPT_DIR/vault"

# Files to encrypt additionally
ADDITIONAL_FILES=(
    "$SCRIPT_DIR/Dockerfile.be.dev"
    "$SCRIPT_DIR/Dockerfile.fe.dev"
)

# Process each file in .secret directory
for file in "$SECRET_DIR"/*; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        encrypted_file="$VAULT_DIR/${filename}.enc"
        
        echo "Encrypting $filename..."
        
        # Encrypt the file using openssl
        echo "$PASSWORD" | openssl enc -aes-256-cbc -salt -pbkdf2 -in "$file" -out "$encrypted_file" -pass stdin
        
        if [ $? -eq 0 ]; then
            echo "Successfully encrypted $filename to $encrypted_file"
        else
            echo "Error encrypting $filename"
        fi
    fi
done

# Process additional files
for file in "${ADDITIONAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        encrypted_file="$VAULT_DIR/${filename}.enc"
        
        echo "Encrypting $filename..."
        
        # Encrypt the file using openssl
        echo "$PASSWORD" | openssl enc -aes-256-cbc -salt -pbkdf2 -in "$file" -out "$encrypted_file" -pass stdin
        
        if [ $? -eq 0 ]; then
            echo "Successfully encrypted $filename to $encrypted_file"
        else
            echo "Error encrypting $filename"
        fi
    fi
done

echo "Encryption complete. Encrypted files are stored in $VAULT_DIR"
