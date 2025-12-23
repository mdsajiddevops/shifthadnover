#!/bin/bash
cd ~/shifthandover_v3
echo "Looking for @db references..."
grep -rn "@db/" *.py routes/*.py models/*.py services/*.py 2>/dev/null

echo ""
echo "Looking for DATABASE_URL with db..."
grep -rn "DATABASE_URL" *.py routes/*.py models/*.py config.py 2>/dev/null | grep -v shift-db

echo ""
echo "Looking in config.py..."
cat config.py | grep -i database




