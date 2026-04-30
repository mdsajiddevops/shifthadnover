#!/bin/bash
cd ~/shifthandover_v3
python3 << 'EOF'
import zipfile
z = zipfile.ZipFile('full_update.zip')
z.extractall('.')
z.close()
print("Extracted files count:", len(z.namelist()))
EOF
rm -f full_update.zip
ls -la templates/shift_roster.html
echo "Files extracted successfully"

