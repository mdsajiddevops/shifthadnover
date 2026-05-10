# Secrets

This directory is gitignored. To set up locally, create each file with the real value:

  secrets/flask_secret_key       — Flask session signing key
  secrets/database_url           — Full DB connection string
  secrets/mysql_password         — MySQL app user password
  secrets/mysql_root_password    — MySQL root password
  secrets/mysql_user_password    — MySQL user password
  secrets/secrets_master_key     — Master encryption key
  secrets/smtp_password          — SMTP relay password
  secrets/smtp_username          — SMTP relay username
  secrets/sso_encryption_key     — SSO token encryption key

Ask the team lead for the values. Never commit this directory.
