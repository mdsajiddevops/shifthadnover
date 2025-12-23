#!/bin/bash
# Complete setup guide for nginx SSL reverse proxy

cat << 'EOF'
🚀 NGINX SSL REVERSE PROXY SETUP GUIDE
=====================================

This guide will help you set up nginx as an SSL reverse proxy for your Shift Handover application.

📋 PREREQUISITES:
- GCP VM with Docker and Docker Compose installed
- Application running on port 5000
- PFX certificate file
- SSH access to the VM

🔧 SETUP STEPS:

1️⃣ CONNECT TO YOUR VM:
   ssh -i ~/.ssh/my-gcp-key shifthandoversajid@10.82.143.226

2️⃣ UPLOAD FILES TO VM:
   # From your local machine, upload the nginx configuration files:
   scp -i ~/.ssh/my-gcp-key -r ./nginx/ shifthandoversajid@10.82.143.226:~/shifthandover_v3/

3️⃣ INSTALL NGINX ON VM:
   cd ~/shifthandover_v3/nginx
   chmod +x *.sh
   sudo ./setup-nginx.sh

4️⃣ UPLOAD YOUR PFX CERTIFICATE:
   # Upload your PFX certificate to the VM
   scp -i ~/.ssh/my-gcp-key /path/to/your/certificate.pfx shifthandoversajid@10.82.143.226:~/

5️⃣ CONVERT CERTIFICATE:
   cd ~
   ~/shifthandover_v3/nginx/convert-certificate.sh certificate.pfx YOUR_CERTIFICATE_PASSWORD

6️⃣ DEPLOY NGINX CONFIGURATION:
   cd ~/shifthandover_v3/nginx
   sudo ./deploy-nginx.sh

7️⃣ UPDATE DOCKER COMPOSE (OPTIONAL):
   # If you want to run nginx in Docker instead of directly on VM:
   # Merge docker-compose-nginx.yml with your existing docker-compose.yml

8️⃣ UPDATE SSO CONFIGURATION:
   ./fix-sso-redirect.sh

9️⃣ RESTART APPLICATION:
   cd ~/shifthandover_v3
   docker-compose restart shift-web

🔒 FIREWALL CONFIGURATION:
   # Make sure ports 80 and 443 are open in GCP firewall
   gcloud compute firewall-rules create allow-https --allow tcp:443 --source-ranges 0.0.0.0/0
   gcloud compute firewall-rules create allow-http --allow tcp:80 --source-ranges 0.0.0.0/0

✅ VERIFICATION:
   1. Check nginx status: sudo systemctl status nginx
   2. Test SSL: curl -k https://10.82.143.226
   3. Check application: https://10.82.143.226
   4. Test SSO login

🌐 AFTER SETUP:
   - Your app will be available at: https://10.82.143.226
   - HTTP traffic will automatically redirect to HTTPS
   - SSO should work with the new HTTPS URLs

🔧 TROUBLESHOOTING:
   - Check nginx logs: sudo tail -f /var/log/nginx/error.log
   - Check application logs: docker logs shift-web
   - Test nginx config: sudo nginx -t
   - Reload nginx: sudo systemctl reload nginx

📝 NOTES:
   - Keep your PFX certificate secure
   - Update DNS to point your domain to 10.82.143.226
   - Consider setting up automated certificate renewal
   - Monitor logs for any SSL/proxy issues

EOF