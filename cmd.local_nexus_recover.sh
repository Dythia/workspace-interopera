#!/bin/bash

# Script to import the latest nexus SQL dump into the postgres database

# Find the latest nexus dump file
LATEST_FILE=$(ls -t .sql/nexus_dump_*.sql | head -1)

if [ -z "$LATEST_FILE" ]; then
    echo "No nexus dump files found in .sql directory"
    exit 1
fi

echo "Importing $LATEST_FILE into postgres nexus database..."

# Import the dump
cat "$LATEST_FILE" | docker exec -i postgres psql -U postgres -d nexus

echo "Import completed."