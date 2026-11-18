# TALVOA | Safe partner schema rehearsal on verified WORK clone only.
# Default = DRY RUN (BEGIN + migration SQL + ROLLBACK).
# -Apply is intentionally separate and should be used only AFTER dry-run was reviewed.
param(
    [switch]$Apply,
    [string]$SqlFile = (Join-Path $env:USERPROFILE "talvoa-partner-local.sql")
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$pg = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
$work = Join-Path $env:USERPROFILE "TALVOA_Local_Work\pgdata"
$database = "talvoa_local_work_20261116"
$username = "talvoa_work_owner"
$hostName = "127.0.0.1"
$port = "60440"
if (-not (Test-Path -LiteralPath $pg -PathType Leaf)) { throw "PostgreSQL 17 psql.exe not found." }
if (-not (Test-Path -LiteralPath $SqlFile -PathType Leaf)) { throw "SQL migration file not found: $SqlFile" }
if (-not (Test-Path -LiteralPath (Join-Path $work "PG_VERSION") -PathType Leaf)) { throw "Work clone missing: $work" }
if ((Get-Content -LiteralPath (Join-Path $work "PG_VERSION") -Raw).Trim() -ne "17") {
    throw "Unexpected PostgreSQL major version. STOP."
}
if ($Apply) {
    Write-Host "APPLY requested: changes will be committed ONLY in $database on port $port." -ForegroundColor Yellow
} else {
    Write-Host "DRY RUN: migration will execute inside a transaction and ROLLBACK." -ForegroundColor Cyan
}
$secure = Read-Host "Senha do PostgreSQL TALVOA LOCAL (nao compartilhe)" -AsSecureString
$credential = [System.Net.NetworkCredential]::new("",$secure)
try {
    $env:PGPASSWORD = $credential.Password
    # Verify cluster identity (prevents connecting to a different server on the expected port).
    $serverDir = & $pg -X -w -v ON_ERROR_STOP=1 -h $hostName -p $port -U $username -d $database -Atc "SHOW data_directory;"
    if ($LASTEXITCODE -ne 0) { throw "Could not authenticate or inspect local work cluster." }
    $expected = [System.IO.Path]::GetFullPath($work).TrimEnd('\','/')
    $actual = [System.IO.Path]::GetFullPath(($serverDir | Select-Object -Last 1).Trim()).TrimEnd('\','/')
    if (-not $actual.Equals($expected,[StringComparison]::OrdinalIgnoreCase)) {
        throw "Cluster directory mismatch: STOP. No migration attempted."
    }

    $psqlArgs = @("-X","-w","-v","ON_ERROR_STOP=1","-h",$hostName,"-p",$port,"-U",$username,"-d",$database)
    if ($Apply) {
        # -1 forces SQL to execute and commit as a SINGLE transaction.
        & $pg @psqlArgs "--single-transaction" "-f" $SqlFile
    } else {
        # SQL executes (including DDL) but is never persisted on the work clone.
        & $pg @psqlArgs "-c" "BEGIN;" "-f" $SqlFile "-c" "ROLLBACK;"
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Migration validation failed. Any open transaction was rolled back; DO NOT retry without review."
    }

    # A separate connection proves the final committed state.
    $check = @'
SELECT count(*)::text || ':' ||
       (SELECT count(*) FROM public.companies_v2)::text || ':' ||
       (SELECT count(*) FROM public.users_v2)::text || ':' ||
       (SELECT count(*) FROM public.company_units)::text || ':' ||
       (SELECT count(*) FROM public.company_sectors)::text || ':' ||
       (SELECT count(*) FROM public.printers)::text || ':' ||
       (SELECT count(*) FROM public.printer_usage_daily)::text || ':' ||
       (SELECT count(*) FROM public.operational_alerts)::text
  FROM information_schema.tables
 WHERE table_schema='public' AND table_type='BASE TABLE';
'@
    $state = & $pg @psqlArgs "-Atc" $check
    if ($LASTEXITCODE -ne 0) { throw "Unable to verify state after migration." }
    $state = ($state | Select-Object -Last 1).Trim()
    $expectedState = if ($Apply) { "9:3:3:3:25:35:1080:154" } else { "7:3:3:3:25:35:1080:154" }
    if ($state -ne $expectedState) {
        throw "Unexpected database state after run. Got $state (expected $expectedState). STOP."
    }
    if ($Apply) {
        Write-Host "APPLY VALIDATED: 9 tables, preserved 1303 historical rows." -ForegroundColor Green
    } else {
        Write-Host "DRY RUN VALIDATED: transaction rolled back; original 7 tables / 1303 rows remain." -ForegroundColor Green
    }
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    $secure = $null
    $credential = $null
}
