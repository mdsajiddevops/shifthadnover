#!/bin/bash

# Manual deployment script for testing
# Use this to deploy manually before setting up the pipeline

DOCKER_USERNAME="your-dockerhub-username"
IMAGE_NAME="shift-handover-app"
IMAGE_TAG="latest"

echo "🚀 Manual deployment to GCP VM..."

# Stop existing container
echo "🛑 Stopping existing container..."
sudo docker stop shift-handover-app || true
sudo docker rm shift-handover-app || true

# Pull latest image
echo "📥 Pulling latest image..."
sudo docker pull $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG

# Run new container
echo "🏃 Starting new container..."
sudo docker run -d \
  --name shift-handover-app \
  --restart unless-stopped \
  -p 80:5000 \
  --env-file /opt/shift-handover-app/.env \
  $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG

# Check status
echo "📊 Checking container status..."
sudo docker ps | grep shift-handover-app

# Health check
echo "🏥 Performing health check..."
sleep 30
if curl -f http://localhost/; then
  echo "✅ Deployment successful!"
else
  echo "❌ Health check failed"
  sudo docker logs shift-handover-app
  exit 1
fi