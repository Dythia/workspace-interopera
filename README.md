# workspace-interopera

# Prerequisites
```bash
   docker context create net.rgs.dev05 --docker "host=ssh://net.rgs.dev05"
   docker context use net.rgs.dev05
```

# Build Base Docker Image
```bash
  cd ~/Git/workspace-global && docker build -f Dockerfile.rgs-python-base -t rgs-python-base .
```
# Tunnel to Dev Machine
```bash
    ssh -vvvv -N \
    -L 5432:localhost:5432 \
    -L 8000:localhost:8000 \
    -L 3000:localhost:3000 \
    -L 6379:localhost:6379 \
    -L 8385:localhost:8384 \
    net.rgs.dev05
```

# Deploy Base Stack
```bash
  docker run -d --name redis -p 6379:6379 -v redisdata:/data redis:6.2
  docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
  docker run --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d pgvector/pgvector:pg16
  docker exec -u postgres postgres psql -d template1 -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

# Deploy DB
```bash
    # Create databases (only needed first time)
    docker exec -u postgres postgres psql -c "CREATE DATABASE rpmm;"
    docker exec -u postgres postgres psql -c "CREATE DATABASE nexus;"
    bash cmd.local_nexus_recover.sh
    bash cmd.loca_rpmm_recover.sh
```

# Build Docker Image FE & BE
```bash
  # First, clone the repository (if not already cloned)
  ./cmd.clone.sh

  # Then build the images
  # Run the interactive build script
  # Choose to build: both, backend-only, or frontend-only
  ./cmd.build.sh
```

# Run Docker Image FE & BE
```bash
  # BE
  docker stop interopera-nexus-be  && docker rm interopera-nexus-be
  docker run -d --name interopera-nexus-be -w /app\
    -v /app/Sales-Manager:/app \
    -v /app/Sales-Manager/.env:/app/.env \
    --add-host host.postgres:host-gateway \
    --add-host host.redis:host-gateway \
    --add-host host.rabbitmq:host-gateway \
    -p 8000:8000 \
    interopera-nexus-be:main
``` 

```bash
  # FE
  docker stop interopera-nexus-fe  && docker rm interopera-nexus-fe
  # Install frontend dependencies in the mounted directory
  ./cmd.install-fe-deps.sh
  # Then run the container
  docker run -d --name interopera-nexus-fe -w /app \
    -v /app/Sales-Manager/frontend:/app \
    -v /app/Sales-Manager/frontend/.env.local:/app/.env.local \
    -p 3000:3000 \
    interopera-nexus-fe:main
``` 

# Recovery DB to local
```bash
  docker exec -i postgres psql -U postgres -c 'DROP DATABASE IF EXISTS nexus;'
  docker exec -i postgres psql -U postgres -c 'CREATE DATABASE nexus;'
  
  docker exec -i postgres psql -U postgres -c 'DROP DATABASE IF EXISTS rpmm;'
  docker exec -i postgres psql -U postgres -c 'CREATE DATABASE rpmm;'

  bash cmd.local_nexus_recover.sh
  bash cmd.local_rpmm_recover.sh
```

# Dump DEVELOP SERVER DB 
```bash
  # Run the database dump script (it will prompt for password)
  ./cmd.db_dump.sh
```

# Dump DB PRODUCTION DB
```bash
  # Run the production database dump script (it will prompt for password)
  ./cmd.db_dump_prod.sh
```

# Peform Migration on Dev
```bash
  # Set environment variables (will prompt for password)
  ./cmd.migration.set_env_dev.sh

  # Then run migration commands
  alembic -c alembic_rpmm.ini current
  alembic -c alembic_rpmm.ini history  
  alembic -c alembic_rpmm.ini show head

  alembic -c alembic.ini history  
  alembic -c alembic.ini show head
  alembic -c alembic.ini current

```

# Peform Migration on Prod
```bash
  # Set environment variables (will prompt for password)
  ./cmd.migration.set_env_prod.sh

  # Then run migration commands
  alembic -c alembic.ini current
  alembic -c alembic.ini history  
  alembic -c alembic.ini show head

  alembic -c alembic_rpmm.ini current
  alembic -c alembic_rpmm.ini history  
  alembic -c alembic_rpmm.ini show head
```


