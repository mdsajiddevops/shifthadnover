#!/bin/bash
cd ~/shifthandover_v3

# Stop and remove container
docker stop shift-web 2>/dev/null
docker rm shift-web 2>/dev/null

# Start container with all necessary environment variables
echo "Starting container with proper environment..."
docker run -d \
    --name shift-web \
    --network shifthandover-net \
    -p 5000:5000 \
    -v "$(pwd):/app" \
    -e FLASK_ENV=production \
    -e FLASK_APP=app.py \
    -e FLASK_DEBUG=0 \
    -e DATABASE_HOST=shift-db \
    -e DATABASE_PORT=3306 \
    -e DATABASE_NAME=shifthandover \
    -e DATABASE_USER=user \
    -e DATABASE_PASSWORD=userpassword \
    shift-web \
    bash -c "/app/start.sh"

sleep 10
echo "Checking container environment..."
docker exec shift-web env | grep -i database

echo ""
echo "Testing app..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:5000/login

echo ""
echo "Container logs:"
docker logs shift-web --tail 20







