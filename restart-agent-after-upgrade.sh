#!/bin/bash

# Post-upgrade script to restart Azure DevOps agent
echo "🔄 Restarting Azure DevOps Agent after VM upgrade..."

# Wait for VM to be fully ready
sleep 30

# Restart agent service
ssh -i gcp_ssh_key shifthandoversajid@35.200.202.18 "cd ~/myagent && sudo ./svc.sh restart"

# Check agent status
ssh -i gcp_ssh_key shifthandoversajid@35.200.202.18 "cd ~/myagent && sudo ./svc.sh status"

echo "✅ Agent restart complete!"
echo "🎯 Your pipeline should now run more efficiently with 4GB RAM!"