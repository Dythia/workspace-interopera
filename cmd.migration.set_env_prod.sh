#!/bin/bash

# Prompt for PGPASSWORD
read -s -p "Enter PGPASSWORD for production: " PGPASSWORD
echo

# Set environment variables for production
export DATABASE_URL="postgresql+asyncpg://root:${PGPASSWORD}@nexus-cluster.cluster-cusn9zi3vp6l.ap-southeast-1.rds.amazonaws.com:5432/nexus"
export RPMM_DATABASE_URL="postgresql+asyncpg://root:${PGPASSWORD}@nexus-cluster.cluster-cusn9zi3vp6l.ap-southeast-1.rds.amazonaws.com:5432/rpmm"

echo "Production environment variables set:"
echo "DATABASE_URL=$DATABASE_URL"
echo "RPMM_DATABASE_URL=$RPMM_DATABASE_URL"
echo
echo "You can now run alembic commands for production migration."
