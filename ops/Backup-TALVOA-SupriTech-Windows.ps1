# TALVOA SupriTech — controlled Windows backup, no cloud upload.
# Run interactively only on an authorized Windows workstation with PostgreSQL 16+ tools.
# Database must allowlist the workstation's public IP. No public firewall changes.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$BackupDir,
  [string]$PgBin = "C:\Program Files\PostgreSQL\16\bin",
  [string]$DbUser = "talvoa_supritech_homolog_db_user"
)
$ErrorActionPreference = 'Stop'
$hostName = 'dpg-db7rsb25b2lc739g0img-a.oregon-postgres.render.com'
$dbName = 'talvoa_supritech_homolog_db'
$dumpTool = Join-Path $PgBin 'pg_dump.exe'
$restoreTool = Join-Path $PgBin 'pg_restore.exe'
if (!(Test-Path -LiteralPath $dumpTool) -or !(Test-Path -LiteralPath $restoreTool)) {
    throw 'PostgreSQL client 16+ missing: select its bin directory with -PgBin.'
}
$ver = (& $dumpTool --version | Out-String)
if ($LASTEXITCODE -ne 0 -or $ver -notmatch 'PostgreSQL\)\s+(\d+)') { throw 'Cannot verify pg_dump version.' }
if ([int]$Matches[1] -lt 16) { throw 'pg_dump 16 or newer required.' }
if (!(Test-Path -LiteralPath $BackupDir -PathType Container)) { throw 'BackupDir must exist on protected local storage.' }
$folder = (Resolve-Path -LiteralPath $BackupDir).Path
if ($folder -match '(?i)\\(github|codespaces|onedrive|dropbox)\\') {
    throw 'Do not place customer backups in synced/source-controlled folders.'
}
$pass = Read-Host 'Render PostgreSQL database password (not printed)' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass)
$destination = Join-Path $folder ("talvoa-supritech-{0}.dump" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
$temp = "$destination.partial"
try {
    $env:PGHOST = $hostName
    $env:PGPORT = '5432'
    $env:PGDATABASE = $dbName
    $env:PGUSER = $DbUser
    $env:PGSSLMODE = 'require'
    $env:PGCONNECT_TIMEOUT = '10'
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    if (Test-Path -LiteralPath $temp) { throw 'Temporary destination already exists.' }
    & $dumpTool --format=custom --no-owner --no-acl --file=$temp
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed; verify IP allowlist, credentials, and TLS.' }
    if (!(Test-Path -LiteralPath $temp) -or (Get-Item -LiteralPath $temp).Length -eq 0) { throw 'Empty dump.' }
    & $restoreTool --list $temp | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Backup archive validation failed.' }
    Move-Item -LiteralPath $temp -Destination $destination -ErrorAction Stop
    $hash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    Set-Content -LiteralPath "$destination.sha256" -Value $hash -Encoding ascii
    Write-Host "BACKUP FILE CREATED: $destination"
    Write-Host "SHA-256: $hash"
    Write-Warning 'Archive verified, but RESTORE NOT TESTED. Encrypt and store independently before any cutover.'
}
finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Force }
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    foreach ($key in @('PGHOST','PGPORT','PGDATABASE','PGUSER','PGSSLMODE','PGCONNECT_TIMEOUT')) {
        Remove-Item "Env:$key" -ErrorAction SilentlyContinue
    }
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
