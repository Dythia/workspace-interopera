#!/bin/bash

# Prompt for PGPASSWORD
read -s -p "Enter PGPASSWORD for development: " PGPASSWORD
echo

# Set environment variables for development
export DATABASE_URL="postgresql+asyncpg://root:${PGPASSWORD}@nexus-cluster.cluster-c6bf21iq8mox.ap-southeast-1.rds.amazonaws.com:5432/nexus"
export RPMM_DATABASE_URL="postgresql+asyncpg://root:${PGPASSWORD}@nexus-cluster.cluster-c6bf21iq8mox.ap-southeast-1.rds.amazonaws.com:5432/rpmm"

echo "Development environment variables set:"
echo "DATABASE_URL=$DATABASE_URL"
echo "RPMM_DATABASE_URL=$RPMM_DATABASE_URL"
echo
echo "You can now run alembic commands for development migration."
