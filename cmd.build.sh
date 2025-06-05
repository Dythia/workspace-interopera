#!/bin/bash

# Script to build Docker images with prompted parameters

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Docker Image Builder for InterOpera${NC}"
echo "=================================="

# Prompt for build type
echo -e "${BLUE}What would you like to build?${NC}"
echo "1) Both Backend and Frontend (default)"
echo "2) Backend only"
echo "3) Frontend only"
echo -e "${YELLOW}Enter choice (1-3):${NC}"
read BUILD_CHOICE
BUILD_CHOICE=${BUILD_CHOICE:-1}

case $BUILD_CHOICE in
    1)
        BUILD_TYPE="both"
        echo -e "${GREEN}Building both Backend and Frontend${NC}"
        ;;
    2)
        BUILD_TYPE="backend"
        echo -e "${GREEN}Building Backend only${NC}"
        ;;
    3)
        BUILD_TYPE="frontend"
        echo -e "${GREEN}Building Frontend only${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice. Building both by default.${NC}"
        BUILD_TYPE="both"
        ;;
esac

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

# Prompt for branch with default
echo -e "${YELLOW}Enter Sales-Manager branch (default: main):${NC}"
read SALES_MANAGER_BRANCH
SALES_MANAGER_BRANCH=${SALES_MANAGER_BRANCH:-main}

echo -e "${GREEN}Using branch: ${SALES_MANAGER_BRANCH}${NC}"

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Track build results
BACKEND_SUCCESS=false
FRONTEND_SUCCESS=false

# Build Backend Image
if [ "$BUILD_TYPE" = "both" ] || [ "$BUILD_TYPE" = "backend" ]; then
    echo -e "${YELLOW}Building Backend Image...${NC}"
    if docker build --build-arg SALES_MANAGER_BRANCH="$SALES_MANAGER_BRANCH" --build-arg GITHUB_TOKEN="$GITHUB_TOKEN" -f "$SCRIPT_DIR/Dockerfile.be.dev" -t "interopera-nexus-be:$SALES_MANAGER_BRANCH" .; then
        echo -e "${GREEN}✅ Backend image built successfully: interopera-nexus-be:$SALES_MANAGER_BRANCH${NC}"
        BACKEND_SUCCESS=true
    else
        echo -e "${RED}❌ Backend image build failed${NC}"
        if [ "$BUILD_TYPE" = "backend" ]; then
            exit 1
        fi
    fi
fi

# Build Frontend Image
if [ "$BUILD_TYPE" = "both" ] || [ "$BUILD_TYPE" = "frontend" ]; then
    echo -e "${YELLOW}Building Frontend Image...${NC}"
    if docker build --build-arg SALES_MANAGER_BRANCH="$SALES_MANAGER_BRANCH" --build-arg GITHUB_TOKEN="$GITHUB_TOKEN" -f "$SCRIPT_DIR/Dockerfile.fe.dev" -t "interopera-nexus-fe:$SALES_MANAGER_BRANCH" .; then
        echo -e "${GREEN}✅ Frontend image built successfully: interopera-nexus-fe:$SALES_MANAGER_BRANCH${NC}"
        FRONTEND_SUCCESS=true
    else
        echo -e "${RED}❌ Frontend image build failed${NC}"
        if [ "$BUILD_TYPE" = "frontend" ]; then
            exit 1
        fi
    fi
fi

# Summary
echo ""
echo -e "${GREEN}🎉 Build Summary:${NC}"

if [ "$BUILD_TYPE" = "both" ] || [ "$BUILD_TYPE" = "backend" ]; then
    if [ "$BACKEND_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ Backend: interopera-nexus-be:$SALES_MANAGER_BRANCH${NC}"
    else
        echo -e "${RED}❌ Backend: Failed${NC}"
    fi
fi

if [ "$BUILD_TYPE" = "both" ] || [ "$BUILD_TYPE" = "frontend" ]; then
    if [ "$FRONTEND_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ Frontend: interopera-nexus-fe:$SALES_MANAGER_BRANCH${NC}"
    else
        echo -e "${RED}❌ Frontend: Failed${NC}"
    fi
fi

# Check if any builds succeeded
if [ "$BACKEND_SUCCESS" = false ] && [ "$FRONTEND_SUCCESS" = false ]; then
    echo -e "${RED}No images were built successfully.${NC}"
    exit 1
fi

echo -e "${GREEN}Build process completed!${NC}"
