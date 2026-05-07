#!/bin/bash
cd ~/shifthandover_v3
docker stop shift-web 2>/dev/null
docker rm shift-web 2>/dev/null

# Fix password in start.sh
sed -i 's/user:password@/user:userpassword@/g' start.sh
sed -i "s/password='password'/password='userpassword'/g" start.sh

# Verify
echo "Checking password config:"
grep -E "password=" start.sh | head -3

# Start the container
echo "Starting container..."
docker run -d \
    --name shift-web \
    --network shifthandover-net \
    -p 5000:5000 \
    -v "$(pwd):/app" \
    -e FLASK_ENV=production \
    -e FLASK_APP=app.py \
    shift-web \
    bash -c "/app/start.sh"

sleep 10
echo "Container logs:"
docker logs shift-web --tail 30







