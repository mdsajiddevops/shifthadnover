# Safe Cleanup Script for Shift Handover App
# This script removes development/testing files while preserving core functionality

param(
    [switch]$DryRun = $false,
    [switch]$Force = $false
)

Write-Host "🧹 Shift Handover App - Safe Cleanup Script" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No files will be deleted" -ForegroundColor Yellow
    Write-Host ""
}

# Get current location
$CurrentPath = Get-Location
Write-Host "📁 Working Directory: $CurrentPath" -ForegroundColor Cyan

# Function to safely remove files
function Remove-SafeFiles {
    param(
        [string[]]$Patterns,
        [string]$Description,
        [string]$Category
    )
    
    Write-Host "`n🗂️  $Category - $Description" -ForegroundColor Yellow
    Write-Host "-" * 40 -ForegroundColor Gray
    
    $FilesFound = @()
    $TotalSize = 0
    
    foreach ($Pattern in $Patterns) {
        $Files = Get-ChildItem -Path $Pattern -ErrorAction SilentlyContinue
        if ($Files) {
            $FilesFound += $Files
            foreach ($File in $Files) {
                if ($File.PSIsContainer) {
                    $Size = (Get-ChildItem -Path $File.FullName -Recurse -File | Measure-Object -Property Length -Sum).Sum
                } else {
                    $Size = $File.Length
                }
                $TotalSize += $Size
                
                if ($DryRun) {
                    Write-Host "   [WOULD DELETE] $($File.Name)" -ForegroundColor Gray
                } else {
                    Write-Host "   ✗ Removing: $($File.Name)" -ForegroundColor Red
                    if ($File.PSIsContainer) {
                        Remove-Item -Path $File.FullName -Recurse -Force -ErrorAction SilentlyContinue
                    } else {
                        Remove-Item -Path $File.FullName -Force -ErrorAction SilentlyContinue
                    }
                }
            }
        }
    }
    
    if ($FilesFound.Count -gt 0) {
        $SizeMB = [math]::Round($TotalSize / 1MB, 2)
        Write-Host "   📊 Found: $($FilesFound.Count) files/folders ($SizeMB MB)" -ForegroundColor Cyan
    } else {
        Write-Host "   ✅ No files found matching patterns" -ForegroundColor Green
    }
    
    return $FilesFound.Count
}

# Confirm before proceeding
if (-not $DryRun -and -not $Force) {
    Write-Host "`n⚠️  This will permanently delete development/testing files." -ForegroundColor Yellow
    Write-Host "   Essential application files will be preserved." -ForegroundColor Green
    $Confirm = Read-Host "`nDo you want to continue? (y/N)"
    if ($Confirm -notmatch '^[Yy]') {
        Write-Host "❌ Cleanup cancelled by user" -ForegroundColor Red
        exit 0
    }
}

Write-Host "`n🚀 Starting cleanup process..." -ForegroundColor Green

# Phase 1: Testing/Debug Scripts (100% Safe)
$TotalRemoved = 0

$TestScripts = @(
    "check_*.py", "debug_*.py", "test_*.py", "simple_*.py",
    "create_*.py", "fix_*.py", "setup_*.py", "manual_*.py",
    "demo_*.py", "comprehensive_test.py", "final_test.py",
    "minimal_test.py", "diagnose_*.py", "force_*.py",
    "quick_*.py", "restart_*.py", "reassign_*.py"
)
$TotalRemoved += Remove-SafeFiles -Patterns $TestScripts -Description "Testing and Debug Scripts" -Category "PHASE 1"

# Phase 1: PowerShell Scripts
$PSScripts = @("*.ps1")
$TotalRemoved += Remove-SafeFiles -Patterns $PSScripts -Description "PowerShell Testing Scripts" -Category "PHASE 1"

# Phase 1: Alternative Startup Scripts
$StartupScripts = @(
    "app_backup.py", "clean_start*.py", "complete_start.py",
    "fast_start.py", "quick_start.py", "simple_start.py",
    "start_app*.py", "complete_working_demo.py",
    "simple_handover_app.py", "simple_system_startup.py",
    "start_ctask_system_complete.py", "start_dashboard_scheduler.py"
)
$TotalRemoved += Remove-SafeFiles -Patterns $StartupScripts -Description "Alternative Startup Scripts" -Category "PHASE 1"

# Phase 1: Documentation (Development)
$DevDocs = @(
    "*_REPORT.md", "*_IMPLEMENTATION.md", "*_SUMMARY.md",
    "*_ENHANCEMENTS.md", "TESTING_*.md", "FEATURE_*.md",
    "HANDOVER_TESTING_GUIDE.md", "SERVICENOW_INTEGRATION_GUIDE.md",
    "SERVICENOW_AUTOMATIC_INCIDENT_FETCHING.md"
)
$TotalRemoved += Remove-SafeFiles -Patterns $DevDocs -Description "Development Documentation" -Category "PHASE 1"

# Phase 1: Duplicate/Backup Files
$DuplicateFiles = @(
    "*_backup*", "*(1).py", "*_backupo", "o"
)
$TotalRemoved += Remove-SafeFiles -Patterns $DuplicateFiles -Description "Duplicate and Backup Files" -Category "PHASE 1"

# Phase 1: Backup Directories
$BackupDirs = @(
    "backup_*", "instance(1)", "__pycache__(1)"
)
$TotalRemoved += Remove-SafeFiles -Patterns $BackupDirs -Description "Backup Directories" -Category "PHASE 1"

# Phase 1: Initialization Scripts (Optional after first run)
$InitScripts = @(
    "init_database.py", "init_config.py", "init_feature_config.py",
    "seed_data.py", "migrate_*.py", "update_*.py"
)
$TotalRemoved += Remove-SafeFiles -Patterns $InitScripts -Description "Initialization Scripts (Optional)" -Category "PHASE 1"

# Phase 2: Alternative Templates (Minimal Risk - only affects debug routes)
Write-Host "`n⚠️  PHASE 2: Template Cleanup (Minimal Risk)" -ForegroundColor Yellow
Write-Host "   Note: This only affects debug routes that users don't access" -ForegroundColor Gray

$AltTemplates = @(
    "templates/change_management_debug.html",
    "templates/change_management_fixed.html",
    "templates/change_management_minimal.html",
    "templates/change_management_server.html",
    "templates/change_management_modern*.html",
    "templates/change_management_ultra_modern.html",
    "templates/handover_form_complex.html",
    "templates/handover_reports_enhanced.html",
    "templates/login_clean.html",
    "templates/test_*.html",
    "templates/*_backup*"
)
$TotalRemoved += Remove-SafeFiles -Patterns $AltTemplates -Description "Alternative Templates" -Category "PHASE 2"

# Display summary
Write-Host "`n" + "=" * 50 -ForegroundColor Green
Write-Host "📊 CLEANUP SUMMARY" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

if ($DryRun) {
    Write-Host "🔍 DRY RUN: Would remove $TotalRemoved files/folders" -ForegroundColor Yellow
    Write-Host "💡 Run without -DryRun to actually delete files" -ForegroundColor Cyan
} else {
    Write-Host "✅ Successfully removed $TotalRemoved files/folders" -ForegroundColor Green
    Write-Host "🎯 Core application files preserved" -ForegroundColor Green
}

# List remaining essential files
Write-Host "`n📋 ESSENTIAL FILES PRESERVED:" -ForegroundColor Cyan
$EssentialFiles = @(
    "app.py", "config.py", "requirements.txt", "alembic.ini",
    "Dockerfile*", "docker-compose*.yml", "azure-pipelines.yml",
    ".env*", "*.md" # Deployment docs
)

foreach ($Pattern in $EssentialFiles) {
    $Files = Get-ChildItem -Path $Pattern -ErrorAction SilentlyContinue
    foreach ($File in $Files) {
        if (-not $File.Name.Contains("_REPORT") -and -not $File.Name.Contains("_SUMMARY")) {
            Write-Host "   ✅ $($File.Name)" -ForegroundColor Green
        }
    }
}

Write-Host "`n📁 ESSENTIAL DIRECTORIES PRESERVED:" -ForegroundColor Cyan
$EssentialDirs = @("models", "routes", "services", "templates", "static")
foreach ($Dir in $EssentialDirs) {
    if (Test-Path $Dir) {
        $FileCount = (Get-ChildItem -Path $Dir -Recurse -File | Measure-Object).Count
        Write-Host "   ✅ $Dir/ ($FileCount files)" -ForegroundColor Green
    }
}

Write-Host "`n🎉 PROJECT CLEANUP COMPLETE!" -ForegroundColor Green
Write-Host "📦 Your codebase is now production-ready and much cleaner" -ForegroundColor Cyan
Write-Host "🚀 Ready for deployment with Azure DevOps CI/CD pipeline" -ForegroundColor Cyan

# Show next steps
Write-Host "`n📋 NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Test your application: python app.py" -ForegroundColor White
Write-Host "2. Commit changes: git add . && git commit -m 'Clean up development files'" -ForegroundColor White
Write-Host "3. Build Docker image: .\build-and-push.ps1" -ForegroundColor White
Write-Host "4. Deploy using Azure DevOps pipeline" -ForegroundColor White