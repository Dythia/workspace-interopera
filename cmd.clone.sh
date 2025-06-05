#!/bin/bash

# Script to clone Sales-Manager repository with prompted GitHub token

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Sales-Manager Repository Cloner${NC}"
echo "==============================="

# Prompt for GitHub token
echo -e "${YELLOW}Enter GitHub token:${NC}"
read -s GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}Error: GitHub token cannot be empty${NC}"
    exit 1
fi

# Confirm token (show first few characters)
TOKEN_PREFIX=$(echo "$GITHUB_TOKEN" | cut -c1-8)
echo -e "${GREEN}Token received: ${TOKEN_PREFIX}...${NC}"

# Check if /app directory exists
if [ ! -d "/app" ]; then
    echo -e "${YELLOW}Creating /app directory...${NC}"
    mkdir -p /app
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to create /app directory${NC}"
        exit 1
    fi
fi

# Change to /app directory
cd /app

# Remove any existing Sales-Manager directory
if [ -d "Sales-Manager" ]; then
    echo -e "${YELLOW}Removing existing Sales-Manager directory...${NC}"
    rm -rf Sales-Manager
fi

# Clone the repository
echo -e "${YELLOW}Cloning Sales-Manager repository...${NC}"
if git clone "https://${GITHUB_TOKEN}@github.com/InterOpera-Apps/Sales-Manager.git"; then
    echo -e "${GREEN}✅ Repository cloned successfully to /app/Sales-Manager${NC}"
else
    echo -e "${RED}❌ Failed to clone repository${NC}"
    echo -e "${YELLOW}Possible causes:${NC}"
    echo "  - Invalid GitHub token"
    echo "  - Network connectivity issues"
    echo "  - Repository access permissions"
    exit 1
fi

# Verify the clone
if [ -d "Sales-Manager" ] && [ -f "Sales-Manager/README.md" ]; then
    echo -e "${GREEN}✅ Clone verification successful${NC}"
    echo -e "${BLUE}Repository contents:${NC}"
    ls -la Sales-Manager/ | head -10
else
    echo -e "${RED}❌ Clone verification failed${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Repository cloned successfully to /app/Sales-Manager!${NC}"
echo -e "${YELLOW}You can now proceed with building the Docker images.${NC}"
