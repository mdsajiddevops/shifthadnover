#!/bin/bash

# Local Docker build and push script
# Use this to test your Docker image before setting up the pipeline

# Configuration
DOCKER_USERNAME="your-dockerhub-username"  # Replace with your Docker Hub username
IMAGE_NAME="shift-handover-app"
IMAGE_TAG="latest"

echo "🐳 Building and pushing Docker image for Shift Handover App..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Login to Docker Hub
echo "🔑 Logging into Docker Hub..."
echo "Please enter your Docker Hub password when prompted:"
docker login --username $DOCKER_USERNAME

if [ $? -ne 0 ]; then
    echo "❌ Docker Hub login failed"
    exit 1
fi

# Build the image
echo "🏗️ Building Docker image..."
docker build -f Dockerfile.prod -t $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

# Tag with build timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker tag $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG $DOCKER_USERNAME/$IMAGE_NAME:$TIMESTAMP

# Push to Docker Hub
echo "📤 Pushing image to Docker Hub..."
docker push $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG
docker push $DOCKER_USERNAME/$IMAGE_NAME:$TIMESTAMP

if [ $? -ne 0 ]; then
    echo "❌ Docker push failed"
    exit 1
fi

# Test the image locally
echo "🧪 Testing image locally..."
docker run -d --name test-shift-handover -p 8080:5000 \
    -e SECRET_KEY=test-key \
    -e FLASK_ENV=production \
    -e DATABASE_URI=sqlite:///test.db \
    $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG

# Wait for container to start
sleep 10

# Health check
if curl -f http://localhost:8080/ > /dev/null 2>&1; then
    echo "✅ Local test successful!"
else
    echo "⚠️ Local test failed, but image was built and pushed"
    echo "Check logs: docker logs test-shift-handover"
fi

# Cleanup test container
docker stop test-shift-handover > /dev/null 2>&1
docker rm test-shift-handover > /dev/null 2>&1

echo ""
echo "🎉 Build and push completed!"
echo "📝 Image details:"
echo "   Repository: $DOCKER_USERNAME/$IMAGE_NAME"
echo "   Tags: $IMAGE_TAG, $TIMESTAMP"
echo "   Size: $(docker images $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG --format "table {{.Size}}" | tail -n 1)"
echo ""
echo "🔗 Docker Hub: https://hub.docker.com/r/$DOCKER_USERNAME/$IMAGE_NAME"
echo ""
echo "📋 Next steps:"
echo "1. Update azure-pipelines.yml with your Docker Hub username"
echo "2. Set up Azure DevOps service connections"
echo "3. Create your pipeline in Azure DevOps"
echo ""