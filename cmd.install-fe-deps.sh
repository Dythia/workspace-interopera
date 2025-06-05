#!/bin/bash

# Script to install frontend dependencies in the mounted directory

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing Frontend Dependencies${NC}"
echo "================================="

# Check if we're in the right directory
if [ ! -d "/app/Sales-Manager/frontend" ]; then
    echo -e "${RED}Error: /app/Sales-Manager/frontend directory not found${NC}"
    echo -e "${YELLOW}Make sure you're running this after cloning the repository${NC}"
    exit 1
fi

# Navigate to frontend directory
cd /app/Sales-Manager/frontend

echo -e "${YELLOW}Installing npm dependencies...${NC}"
if npm install --legacy-peer-deps; then
    echo -e "${GREEN}✅ Frontend dependencies installed successfully${NC}"
    echo -e "${BLUE}Dependencies ready for container mounting${NC}"
else
    echo -e "${RED}❌ Failed to install frontend dependencies${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Frontend setup complete!${NC}"
