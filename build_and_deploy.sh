#!/bin/bash
# Automated build and deployment script for bindermax RunPod container

set -e

# Configuration - UPDATE THESE
DOCKER_USERNAME="${DOCKER_USERNAME:-lukeford22}"
IMAGE_NAME="bindermax"
IMAGE_TAG="latest"
GITHUB_REPO_URL="${GITHUB_REPO_URL:-https://github.com/lukeford22/bindermax.git}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}bindermax RunPod Build & Deploy Script${NC}"
echo -e "${GREEN}========================================${NC}"

# Step 1: Check prerequisites
echo -e "\n${YELLOW}[1/6] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon not running.${NC}"
    exit 1
fi

echo -e "${GREEN} Docker is installed and running${NC}"

# Step 2: Build Docker image
echo -e "\n${YELLOW}[2/6] Building Docker image...${NC}"
echo "This may take 10-15 minutes on first build..."

docker build -f Dockerfile.cloud -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo -e "${GREEN} Image built successfully${NC}"

# Step 3: Tag image
echo -e "\n${YELLOW}[3/6] Tagging image...${NC}"

FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${IMAGE_TAG}"
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${FULL_IMAGE_NAME}

echo -e "${GREEN} Tagged as ${FULL_IMAGE_NAME}${NC}"

# Step 4: Test image locally (optional)
echo -e "\n${YELLOW}[4/6] Test image locally? (y/n)${NC}"
read -r TEST_LOCALLY

if [[ "$TEST_LOCALLY" == "y" ]]; then
    echo "Starting test container..."
    docker run --rm -it \
        -e BINDERMAX_REPO_URL="${GITHUB_REPO_URL}" \
        -e AUTO_DOWNLOAD_MODELS="false" \
        -p 8080:8080 -p 2222:22 \
        ${FULL_IMAGE_NAME} /bin/bash
fi

# Step 5: Push to Docker Hub
echo -e "\n${YELLOW}[5/6] Push to Docker Hub? (y/n)${NC}"
read -r PUSH_IMAGE

if [[ "$PUSH_IMAGE" == "y" ]]; then
    echo "Logging into Docker Hub..."
    docker login

    echo "Pushing image..."
    docker push ${FULL_IMAGE_NAME}

    echo -e "${GREEN} Image pushed successfully${NC}"
else
    echo "Skipping push. You can push later with:"
    echo "  docker push ${FULL_IMAGE_NAME}"
fi

# Step 6: Display deployment instructions
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Build Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Image: ${FULL_IMAGE_NAME}"
echo ""
echo "Next steps for RunPod deployment:"
echo ""
echo "1. Go to https://runpod.io"
echo "2. Navigate to Templates → New Template"
echo "3. Use these settings:"
echo "   - Container Image: ${FULL_IMAGE_NAME}"
echo "   - Container Disk: 50 GB"
echo "   - Volume Disk: 100 GB"
echo "   - Volume Mount Path: /workspace"
echo "   - Expose Ports: HTTP 8080, TCP 22"
echo "   - Environment Variable:"
echo "       CUSTOM_REPO_URL=${GITHUB_REPO_URL}"
echo ""
echo "4. Deploy a Pod using this template"
echo "5. Wait for container to start"
echo "6. Connect via SSH (details in RunPod console)"
echo ""
echo "For detailed instructions, see RUNPOD_DEPLOYMENT.md"
echo ""
