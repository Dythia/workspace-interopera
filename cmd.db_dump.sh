#!/bin/bash

# Prompt for PGPASSWORD
read -s -p "Enter PGPASSWORD: " PGPASSWORD
echo

# Ensure sql directory exists
mkdir -p "$(pwd)/.sql"

pg_dump \
  --host=nexus-cluster.cluster-c6bf21iq8mox.ap-southeast-1.rds.amazonaws.com \
  --port=5432 \
  --username=root \
  --dbname=nexus \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  --encoding=UTF8 \
  --quote-all-identifiers \
  --format=plain \
  --verbose \
  --inserts \
  --file="$(pwd)/.sql/nexus_dump_$(date +%Y%m%d_%H%M%S).sql"

pg_dump \
  --host=nexus-cluster.cluster-c6bf21iq8mox.ap-southeast-1.rds.amazonaws.com \
  --port=5432 \
  --username=root \
  --dbname=rpmm \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  --encoding=UTF8 \
  --quote-all-identifiers \
  --format=plain \
  --verbose \
  --inserts \
  --file="$(pwd)/.sql/rpmm_dump_$(date +%Y%m%d_%H%M%S).sql"

unset PGPASSWORD

echo "Database dumps completed."
