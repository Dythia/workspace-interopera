#!/bin/bash

# Script to import the latest rpmm SQL dump into the postgres database

# Find the latest rpmm dump file
LATEST_FILE=$(ls -t .sql/rpmm_dump_*.sql | head -1)

if [ -z "$LATEST_FILE" ]; then
    echo "No rpmm dump files found in .sql directory"
    exit 1
fi

echo "Importing $LATEST_FILE into postgres rpmm database..."

# Import the dump
cat "$LATEST_FILE" | docker exec -i postgres psql -U postgres -d rpmm

echo "Import completed."