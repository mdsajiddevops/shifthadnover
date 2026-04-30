# PowerShell script to run team email configuration migration on GCP VM

Write-Host "🔄 Running team email configuration migration..." -ForegroundColor Cyan

try {
    # Copy SQL migration to VM
    Write-Host "📤 Copying migration file to GCP VM..." -ForegroundColor Yellow
    scp -i ~/.ssh/id_rsa migrations/add_team_email_columns.sql sajid@10.82.143.226:/tmp/
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to copy migration file to VM"
    }
    
    # Run migration on VM
    Write-Host "🚀 Executing migration on database..." -ForegroundColor Yellow
    
    $sshCommand = @"
echo "📥 Running team email configuration migration..."
docker exec shift-db mysql -u shifthandover_user -pshifthandover_pass shift_handover < /tmp/add_team_email_columns.sql
if [ `$? -eq 0 ]; then
    echo "✅ Team email configuration migration completed successfully!"
    echo "Teams can now have their own email distribution lists."
    rm /tmp/add_team_email_columns.sql
    echo "🧹 Cleaned up migration file"
else
    echo "❌ Migration failed!"
    exit 1
fi
"@
    
    ssh -i ~/.ssh/id_rsa sajid@10.82.143.226 $sshCommand
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Migration completed successfully!" -ForegroundColor Green
        Write-Host "Teams can now configure their own email distribution lists." -ForegroundColor Green
    } else {
        throw "Migration execution failed"
    }
    
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host "🏁 Migration process completed!" -ForegroundColor Green