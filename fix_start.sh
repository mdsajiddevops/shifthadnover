#!/bin/bash
cd ~/shifthandover_v3
docker stop shift-web 2>/dev/null
docker rm shift-web 2>/dev/null

# Fix database host in start.sh
sed -i "s/host='db'/host='shift-db'/g" start.sh
sed -i 's/@db/@shift-db/g' start.sh
sed -i 's/database=.shift_handover./database="shifthandover"/g' start.sh

# Verify the fix
echo "Checking start.sh for database config:"
grep -E "host=|@shift-db|database=" start.sh | head -5

# Start the container
echo "Starting container..."
docker run -d \
    --name shift-web \
    --network shifthandover-net \
    -p 5000:5000 \
    -v "$(pwd):/app" \
    -e FLASK_ENV=production \
    -e FLASK_APP=app.py \
    -e DATABASE_HOST=shift-db \
    -e DATABASE_NAME=shifthandover \
    -e DATABASE_USER=user \
    -e DATABASE_PASSWORD=userpassword \
    shift-web \
    bash -c "/app/start.sh"

sleep 10
echo "Container logs:"
docker logs shift-web --tail 30







