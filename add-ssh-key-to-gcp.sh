#!/bin/bash

# SSH Public Key for Azure DevOps Agent
# Copy this key to your GCP VM's authorized_keys file

echo "=== SSH PUBLIC KEY ==="
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDQLSO5GEcdJqR3ENFwKTIVcVHh0A18DKnZaY2gahcd3F4T6qjq+XyPri6b0qYXi0lTjQDVjXBdLJEXU5/eMIvH7lKfnDN91WBwi/fwz7pgEIcH9k+0eTN3JlZX9zLE27X3EIldvDvC2qnKjUnHDNWEKU6m/OQy/KugYJR4qEuCkBxEVrd8FLhiHorWjK/UNCb+ZJv2b+XugpT4k7rbXGc0mkSd/eT24sR+Ju29CpqgPG9t8PPRXeh3rnn0Xzo8YS+UjXCPyzZ8rhlv6dx6p1eswsYcBu5gXogA7e9vwkIERdxLzt+j493/gMBRUNsD+5JszeyR3E9dvKn7ANTRlSWEnaKGTPvRy4xMpHGx38FCtUUh1vXgllG0CdzlBR/LZp+9I889kIJhhVjco9dL8HaAnW9GExWelIEbclCRI611T+qYCU5vCgPj8EDMxMbV2dLjIS4oxXwtwckwENrmaesgK+0J02isTCCYhOd+Ra0NesTcaAyqd9rBfAkwwTKqgjRk0g21DwDkQkbUDdzYiIsZhg5AvOZi9+00+r3H7wvbfU1AFft+rlSyO35cmSTeFkWtdbaWUybApXGCSTrF8NXrUh2mamocykjVv4M9s3Osba0/iNxpbpx8oelJcNb44NGXlh869Z68w6V/g6rnxjJxLmdIOSy43BsW7aXh2/HD/w== azure-devops-agent"

echo ""
echo "=== INSTRUCTIONS ==="
echo "1. Go to Google Cloud Console: https://console.cloud.google.com/"
echo "2. Navigate to Compute Engine > VM Instances"
echo "3. Find your VM (IP: 35.200.202.18)"
echo "4. Click 'SSH' to open browser terminal"
echo "5. Run these commands:"
echo ""
echo "   mkdir -p ~/.ssh"
echo "   echo 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDQLSO5GEcdJqR3ENFwKTIVcVHh0A18DKnZaY2gahcd3F4T6qjq+XyPri6b0qYXi0lTjQDVjXBdLJEXU5/eMIvH7lKfnDN91WBwi/fwz7pgEIcH9k+0eTN3JlZX9zLE27X3EIldvDvC2qnKjUnHDNWEKU6m/OQy/KugYJR4qEuCkBxEVrd8FLhiHorWjK/UNCb+ZJv2b+XugpT4k7rbXGc0mkSd/eT24sR+Ju29CpqgPG9t8PPRXeh3rnn0Xzo8YS+UjXCPyzZ8rhlv6dx6p1eswsYcBu5gXogA7e9vwkIERdxLzt+j493/gMBRUNsD+5JszeyR3E9dvKn7ANTRlSWEnaKGTPvRy4xMpHGx38FCtUUh1vXgllG0CdzlBR/LZp+9I889kIJhhVjco9dL8HaAnW9GExWelIEbclCRI611T+qYCU5vCgPj8EDMxMbV2dLjIS4oxXwtwckwENrmaesgK+0J02isTCCYhOd+Ra0NesTcaAyqd9rBfAkwwTKqgjRk0g21DwDkQkbUDdzYiIsZhg5AvOZi9+00+r3H7wvbfU1AFft+rlSyO35cmSTeFkWtdbaWUybApXGCSTrF8NXrUh2mamocykjVv4M9s3Osba0/iNxpbpx8oelJcNb44NGXlh869Z68w6V/g6rnxjJxLmdIOSy43BsW7aXh2/HD/w== azure-devops-agent' >> ~/.ssh/authorized_keys"
echo "   chmod 600 ~/.ssh/authorized_keys"
echo "   chmod 700 ~/.ssh"
echo ""
echo "=== THEN CONTINUE WITH AGENT SETUP ==="
echo "After adding the SSH key, run this from Windows:"
echo "   ssh -i gcp_ssh_key shifthandoversajid@35.200.202.18"