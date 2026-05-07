#!/bin/bash
cd ~/shifthandover_v3

# Fix line endings on start.sh if needed
sed -i 's/\r$//' start.sh
chmod +x start.sh

docker run -d \
    --name shift-web \
    --network shifthandover-net \
    -p 5000:5000 \
    -v "$(pwd):/app" \
    -v "$(pwd)/logs:/app/logs" \
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

sleep 5
docker logs shift-web --tail 20

