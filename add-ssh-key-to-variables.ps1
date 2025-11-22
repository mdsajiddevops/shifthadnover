# Script to add SSH private key to Azure DevOps variable group

# Get the SSH private key content
$sshKeyContent = Get-Content -Path "gcp_ssh_key" -Raw

# Add it to variable group as secret
az pipelines variable-group variable create --group-id 1 --name SSH_PRIVATE_KEY --value $sshKeyContent --secret true --org https://dev.azure.com/mdsajid020 --project shift_handover_v2

Write-Host "SSH private key added to variable group successfully!"