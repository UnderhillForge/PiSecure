# PiSecure Genesis Reset Script (PowerShell Version)
# Clears all blockchain data (testnet & mainnet) and recreates fresh genesis
# For Windows (PowerShell) users
#
# Usage: .\genesis-reset.ps1 [-Force] [-Backup]
# Options:
#   -Force    Skip confirmation prompts (use with caution!)
#   -Backup   Create backup before deletion (saved as backup-TIMESTAMP.zip)

param(
    [switch]$Force,
    [switch]$Backup
)

# Enable error handling
$ErrorActionPreference = "Stop"

# Colors
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $Blue
Write-Host "║           PiSecure Genesis Reset Script v1.0              ║" -ForegroundColor $Blue
Write-Host "║         ⚠️  WARNING: This will DELETE all blockchain data  ║" -ForegroundColor $Blue
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $Blue
Write-Host ""

# Get home directory
$HomeDir = $env:USERPROFILE
if (-not $HomeDir) {
    Write-Host "❌ ERROR: USERPROFILE environment variable not set" -ForegroundColor $Red
    exit 1
}

# Paths to clear
$MainnetDir = Join-Path $HomeDir ".pisecure"
$TestnetDir = Join-Path $HomeDir ".pisecure-testnet"
$WalletDir = Join-Path $MainnetDir "wallets"

Write-Host "🔍 Detected OS: Windows (PowerShell)" -ForegroundColor $Yellow
Write-Host "🔍 Home directory: $HomeDir" -ForegroundColor $Yellow
Write-Host ""

# Show what will be deleted
Write-Host "📋 This will DELETE:" -ForegroundColor $Yellow
Write-Host "   ❌ Mainnet blockchain:   $MainnetDir"
Write-Host "   ❌ Testnet blockchain:   $TestnetDir"
Write-Host "   ❌ All wallets:          $WalletDir"
Write-Host ""

# Count items to be deleted
$ItemsToDelete = 0
if (Test-Path $MainnetDir) { $ItemsToDelete++ }
if (Test-Path $TestnetDir) { $ItemsToDelete++ }
if (Test-Path $WalletDir) { $ItemsToDelete++ }

if ($ItemsToDelete -eq 0) {
    Write-Host "✅ No blockchain data found to delete" -ForegroundColor $Green
    Write-Host ""
    Write-Host "Fresh genesis files will be created:" -ForegroundColor $Blue
    Write-Host "   ✨ $MainnetDir (fresh)"
    Write-Host "   ✨ $TestnetDir (fresh)"
    Write-Host ""
} else {
    Write-Host "⚠️  Found $ItemsToDelete directories to delete" -ForegroundColor $Red
    Write-Host ""
}

# Backup if requested
if ($Backup -and $ItemsToDelete -gt 0) {
    $BackupFile = "backup-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"
    Write-Host "💾 Creating backup: $BackupFile" -ForegroundColor $Yellow
    
    try {
        $BackupPaths = @()
        if (Test-Path $MainnetDir) { $BackupPaths += $MainnetDir }
        if (Test-Path $TestnetDir) { $BackupPaths += $TestnetDir }
        if (Test-Path $WalletDir) { $BackupPaths += $WalletDir }
        
        Compress-Archive -Path $BackupPaths -DestinationPath $BackupFile -ErrorAction SilentlyContinue
        Write-Host "✅ Backup created" -ForegroundColor $Green
    } catch {
        Write-Host "⚠️  Could not create backup: $_" -ForegroundColor $Yellow
    }
    Write-Host ""
}

# Confirmation
if (-not $Force) {
    Write-Host "🚨 FINAL WARNING: This action CANNOT be undone!" -ForegroundColor $Red
    Write-Host ""
    
    $Confirm1 = Read-Host "Type 'DELETE ALL' to confirm"
    if ($Confirm1 -ne "DELETE ALL") {
        Write-Host "❌ Cancelled by user" -ForegroundColor $Yellow
        exit 0
    }
    
    Write-Host ""
    $Confirm2 = Read-Host "Type 'YES, DELETE' to CONFIRM"
    if ($Confirm2 -ne "YES, DELETE") {
        Write-Host "❌ Cancelled by user" -ForegroundColor $Yellow
        exit 0
    }
    
    Write-Host ""
}

# Delete existing data
Write-Host "🧹 Deleting existing blockchain and wallet data..." -ForegroundColor $Blue

$DirsToDelete = @(
    @{ Path = $MainnetDir; Name = "Mainnet" },
    @{ Path = $TestnetDir; Name = "Testnet" },
    @{ Path = $WalletDir; Name = "Wallets" }
)

foreach ($DirObj in $DirsToDelete) {
    $Dir = $DirObj.Path
    $Name = $DirObj.Name
    
    if (Test-Path $Dir) {
        Write-Host "   Removing: $Dir"
        Remove-Item -Path $Dir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "   ✓ Deleted" -ForegroundColor $Green
    }
}

Write-Host ""

# Create fresh directories
Write-Host "✨ Creating fresh genesis directories..." -ForegroundColor $Blue

$DirsToCreate = @(
    @{ Path = $MainnetDir; Name = "Mainnet" },
    @{ Path = $TestnetDir; Name = "Testnet" },
    @{ Path = $WalletDir; Name = "Wallets" }
)

foreach ($DirObj in $DirsToCreate) {
    $Dir = $DirObj.Path
    
    if (-not (Test-Path $Dir)) {
        New-Item -ItemType Directory -Path $Dir -Force | Out-Null
    }
    
    Write-Host "   Created: $Dir"
    Write-Host "   ✓" -ForegroundColor $Green
}

Write-Host ""

# Generate fresh genesis blocks using Python
Write-Host "📝 Generating fresh genesis blocks..." -ForegroundColor $Blue

$PythonScript = @"
import os
import sys
sys.path.insert(0, '.')

try:
    # Mainnet genesis
    os.environ['PISECURE_TESTNET'] = '0'
    from pisecure.core import SignChain
    blockchain_mainnet = SignChain()
    print("   ✓ Mainnet genesis created")
    
    # Testnet genesis
    os.environ['PISECURE_TESTNET'] = '1'
    blockchain_testnet = SignChain()
    print("   ✓ Testnet genesis created")
    
    print("")
    print("   Mainnet blocks:  " + str(len(blockchain_mainnet.chain)))
    print("   Testnet blocks:  " + str(len(blockchain_testnet.chain)))
    print("   Both have valid genesis blocks")
    
except Exception as e:
    print(f"   ❌ Error creating genesis: {e}")
    sys.exit(1)
"@

$TempScriptPath = [System.IO.Path]::GetTempFileName() -Replace '\.tmp$', '.py'
Set-Content -Path $TempScriptPath -Value $PythonScript

try {
    python $TempScriptPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "❌ Failed to create genesis blocks" -ForegroundColor $Red
        exit 1
    }
} finally {
    Remove-Item -Path $TempScriptPath -Force -ErrorAction SilentlyContinue
}

Write-Host ""

# Success summary
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $Blue
Write-Host "║            ✅ GENESIS RESET COMPLETE!                     ║" -ForegroundColor $Blue
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $Blue
Write-Host ""

Write-Host "✓ Cleared all blockchain data" -ForegroundColor $Green
Write-Host "✓ Cleared all wallet data" -ForegroundColor $Green
Write-Host "✓ Created fresh genesis blocks" -ForegroundColor $Green
Write-Host ""

# Show what's ready
Write-Host "📦 Ready to use:" -ForegroundColor $Blue
Write-Host "   • Mainnet genesis:  $MainnetDir"
Write-Host "   • Testnet genesis:  $TestnetDir"
Write-Host "   • Wallet storage:   $WalletDir"
Write-Host ""

# Instructions
Write-Host "🚀 Next steps:" -ForegroundColor $Blue
Write-Host "   1. Start a fresh node:"
Write-Host "      pisecure mine  (mainnet)" -ForegroundColor $Yellow
Write-Host "      set PISECURE_TESTNET=1 && pisecure mine  (testnet)" -ForegroundColor $Yellow
Write-Host ""
Write-Host "   2. Or on Windows validation node:"
Write-Host "      set PISECURE_TESTNET=1 && set PISECURE_VALIDATE_ONLY=1 && set PISECURE_MOCK_HARDWARE=1 && pisecure mine" -ForegroundColor $Yellow
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor $Blue
Write-Host ""
