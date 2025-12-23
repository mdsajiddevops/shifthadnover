#!/bin/bash
cd ~/shifthandover_v3

# Stop and remove container
docker stop shift-web 2>/dev/null
docker rm shift-web 2>/dev/null

# Fix database host references in all Python files
echo "Fixing database host references..."
find . -name "*.py" -type f -exec grep -l "host='db'" {} \; | while read file; do
    echo "Fixing $file"
    sed -i "s/host='db'/host='shift-db'/g" "$file"
done

find . -name "*.py" -type f -exec grep -l "@db/" {} \; | while read file; do
    echo "Fixing $file"
    sed -i 's/@db\//@shift-db\//g' "$file"
done

# Also fix the database name from shift_handover to shifthandover
find . -name "*.py" -type f -exec grep -l "shift_handover" {} \; | while read file; do
    echo "Fixing database name in $file"
    sed -i 's/shift_handover/shifthandover/g' "$file"
done

# Fix start.sh
sed -i 's/@db\//@shift-db\//g' start.sh
sed -i 's/shift_handover/shifthandover/g' start.sh

echo "Verifying changes..."
grep -r "host='shift-db'" --include="*.py" . | head -3
grep -r "@shift-db" --include="*.py" . | head -3

# Start container
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
echo "Testing app..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:5000/login
docker logs shift-web --tail 20




