#!/bin/bash
# Script to run team email configuration migration on GCP VM

echo "🔄 Running team email configuration migration..."

# Copy SQL migration to VM
scp -i ~/.ssh/id_rsa migrations/add_team_email_columns.sql sajid@10.82.143.226:/tmp/

# Run migration on VM
ssh -i ~/.ssh/id_rsa sajid@10.82.143.226 << 'EOF'
    echo "📥 Received migration file, connecting to database..."
    
    # Run the SQL migration
    docker exec shift-db mysql -u shifthandover_user -pshifthandover_pass shift_handover < /tmp/add_team_email_columns.sql
    
    if [ $? -eq 0 ]; then
        echo "✅ Team email configuration migration completed successfully!"
        echo "Teams can now have their own email distribution lists."
        
        # Clean up
        rm /tmp/add_team_email_columns.sql
        echo "🧹 Cleaned up migration file"
    else
        echo "❌ Migration failed!"
        exit 1
    fi
EOF

echo "🏁 Migration process completed!"