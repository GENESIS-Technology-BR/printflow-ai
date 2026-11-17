# TALVOA | Recover validation of EXISTING 60440 work clone (read-only SQL).
# Does not recreate cluster, restore dump, reset password or change any data.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$pg = "C:\Program Files\PostgreSQL\17\bin"
$root = Join-Path $env:USERPROFILE "TALVOA_Local_Work"
$data = Join-Path $root "pgdata"
$log = Join-Path $root "postgres-work.log"
$port = 60440
$db = "talvoa_local_work_20261116"
$user = "talvoa_work_owner"
if (-not (Test-Path -LiteralPath (Join-Path $data "PG_VERSION") -PathType Leaf)) {
    throw "Existing clone pgdata not found. STOP; original recovery snapshot must not be used."
}
if ((Get-Content -LiteralPath (Join-Path $data "PG_VERSION") -Raw).Trim() -ne "17") {
    throw "Work pgdata version is not PostgreSQL 17."
}
if (-not (Test-Path -LiteralPath (Join-Path $pg "pg_ctl.exe"))) { throw "PostgreSQL 17 binaries missing." }
$ctl = Join-Path $pg "pg_ctl.exe"
$psql = Join-Path $pg "psql.exe"
$startedHere = $false
try {
    & $ctl -D $data status | Out-Null
    $running = ($LASTEXITCODE -eq 0)
    if (-not $running) {
        if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
            throw "Port $port occupied by another server. Refusing to connect."
        }
        & $ctl -D $data -l $log -o "-c listen_addresses=127.0.0.1 -c port=$port -c max_connections=10" -w start
        if ($LASTEXITCODE -ne 0) { throw "Cannot start existing work cluster." }
        $startedHere = $true
    }
    # A single psql request avoids re-prompting repeatedly and prints only counts,
    # never passwords, printer inventory or other customer data.
    $sql = @'
SELECT current_user AS connected_user, current_database() AS connected_database,
       current_setting('port') AS server_port,
       current_setting('listen_addresses') AS listen_addresses,
       current_setting('data_directory') AS cluster_directory;
SELECT 'companies_v2' AS tabela, COUNT(*) AS registros FROM public.companies_v2
UNION ALL SELECT 'users_v2',COUNT(*) FROM public.users_v2
UNION ALL SELECT 'company_units',COUNT(*) FROM public.company_units
UNION ALL SELECT 'company_sectors',COUNT(*) FROM public.company_sectors
UNION ALL SELECT 'printers',COUNT(*) FROM public.printers
UNION ALL SELECT 'printer_usage_daily',COUNT(*) FROM public.printer_usage_daily
UNION ALL SELECT 'operational_alerts',COUNT(*) FROM public.operational_alerts;
'@
    & $psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p $port -U $user -d $db -c $sql
    if ($LASTEXITCODE -ne 0) {
        throw "Read-only audit FAILED (authentication or SQL). Do not assume count mismatch; do NOT rerun restore."
    }
    Write-Host "SQL AUDIT EXECUTED: Compare 7 counts against 3,3,3,25,35,1080,154 (total 1303)." -ForegroundColor Cyan
} finally {
    if ($startedHere) {
        & $ctl -D $data -m fast -w stop
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Work cluster did not stop cleanly; inspect its state before proceeding."
        }
    }
}
