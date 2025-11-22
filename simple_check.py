from models.models import EscalationMatrixFile
import os
files = EscalationMatrixFile.query.all()
print(" DB Files:\, len(files))
for f in files:
 print(f.filename, f.account_id, f.team_id)
 
upload_folder = \uploads/escalation_matrix\
if os.path.exists(upload_folder):
 disk_files = [f for f in os.listdir(upload_folder) if f.endswith(\.xlsx\)]
 print(\Disk Files:\, disk_files)
else:
 print(\No upload folder\)
