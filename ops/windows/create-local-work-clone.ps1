# TALVOA - Restore a DISTINCT local working cluster from an existing verified dump.
# No cloud writes, no production changes, and no stored passwords.
# Run in a regular PowerShell session under the same Windows account that owns the backup.
# WARNING: this is a work COPY, not a replacement for the preserved recovery cluster.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$pg = "C:\Program Files\PostgreSQL\17\bin"
$root = Join-Path $env:USERPROFILE "TALVOA_Local_Work"
$data = Join-Path $root "pgdata"
$log = Join-Path $root "postgres-work.log"
$dump = Join-Path $env:USERPROFILE "TALVOA_Backups\Printflow-Supabase-20261116-120749.dump"
$port = 60440
$db = "talvoa_local_work_20261116"
$user = "talvoa_work_owner"

function Invoke-Pg([string]$Exe, [string[]]$Argv) {
    & (Join-Path $pg $Exe) @Argv
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed (exit $LASTEXITCODE). Stopping without automatic retry." }
}

foreach ($exe in @("initdb.exe","pg_ctl.exe","pg_restore.exe","pg_isready.exe","createdb.exe","psql.exe")) {
    if (-not (Test-Path -LiteralPath (Join-Path $pg $exe) -PathType Leaf)) { throw "PostgreSQL 17 tool missing: $exe" }
}
if (-not (Test-Path -LiteralPath $dump -PathType Leaf)) { throw "Verified source dump not found: $dump" }
if ([System.IO.File]::ReadAllBytes($dump)[0] -ne 80) { throw "Source file does not resemble a PostgreSQL custom-format dump." }

# Strictly forbid overwriting or reusing the historical recovery cluster.
$preserved = Join-Path $env:USERPROFILE "TALVOA_Restore_Local\pgdata"
if (([System.IO.Path]::GetFullPath($data)).Equals([System.IO.Path]::GetFullPath($preserved), [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to use the preserved recovery cluster."
}
if (Test-Path -LiteralPath $root) { throw "Working directory already exists. Inspect it; no overwrite or cleanup will occur." }
$listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($listener) { throw "Port $port is already in use. Nothing was changed." }

New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
Write-Host "Creating independent WORK database cluster (new password required)." -ForegroundColor Cyan
$started = $false
try {
    # initdb creates a new Windows-local database superuser; -W securely prompts.
    Invoke-Pg "initdb.exe" @("-D",$data,"-U",$user,"-W","--auth-host=scram-sha-256","--auth-local=scram-sha-256","-E","UTF8")

    Invoke-Pg "pg_ctl.exe" @("-D",$data,"-l",$log,"-o","-c listen_addresses=127.0.0.1 -c port=$port -c max_connections=10","-w","start")
    $started = $true

    # pg_isready is not sufficient to identify the intended cluster; verify settings via authenticated connection.
    Invoke-Pg "psql.exe" @("-X","-W","-v","ON_ERROR_STOP=1","-h","127.0.0.1","-p","$port","-U",$user,"-d","postgres","-Atc","SELECT CASE WHEN current_setting('port') = '$port' AND current_setting('listen_addresses') = '127.0.0.1' THEN 1 ELSE 1/0 END;")

    Invoke-Pg "createdb.exe" @("-h","127.0.0.1","-p","$port","-U",$user,"--maintenance-db=postgres","--template=template0",$db)

    # Source RLS policies reference these Supabase roles. They exist *only* in this new cluster.
    Invoke-Pg "psql.exe" @("-X","-W","-v","ON_ERROR_STOP=1","-h","127.0.0.1","-p","$port","-U",$user,"-d","postgres","-c","CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN;")

    Invoke-Pg "pg_restore.exe" @("-h","127.0.0.1","-p","$port","-U",$user,"-d",$db,"--schema=public","--no-owner","--no-acl","--single-transaction","--exit-on-error",$dump)

    # Fail if any of the seven source tables differs from the observed historical counts.
    $sql = @'
WITH expected(table_name, expected_count) AS (
  VALUES ('companies_v2',3::bigint), ('users_v2',3), ('company_units',3),
         ('company_sectors',25), ('printers',35), ('printer_usage_daily',1080),
         ('operational_alerts',154)
),
actual(table_name, actual_count) AS (
 SELECT 'companies_v2', count(*) FROM public.companies_v2 UNION ALL
 SELECT 'users_v2', count(*) FROM public.users_v2 UNION ALL
 SELECT 'company_units', count(*) FROM public.company_units UNION ALL
 SELECT 'company_sectors', count(*) FROM public.company_sectors UNION ALL
 SELECT 'printers', count(*) FROM public.printers UNION ALL
 SELECT 'printer_usage_daily', count(*) FROM public.printer_usage_daily UNION ALL
 SELECT 'operational_alerts', count(*) FROM public.operational_alerts
)
SELECT CASE WHEN count(*) = 7 AND bool_and(e.expected_count=a.actual_count)
            THEN 'VERIFIED_1303' ELSE 'MISMATCH' END
FROM expected e JOIN actual a USING (table_name);
'@
    $result = & (Join-Path $pg "psql.exe") -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p $port -U $user -d $db -Atc $sql
    if ($LASTEXITCODE -ne 0 -or ($result | Select-Object -Last 1) -ne "VERIFIED_1303") {
        throw "Record counts differ from historical source. Do not use this clone."
    }

    Write-Host "WORK CLONE RESTORED AND VERIFIED: 7 tables / 1303 rows" -ForegroundColor Green
    Write-Host "Local mode: ENVIRONMENT=local_homologation, database=$db, port=$port"
    Write-Host "No app has been connected; the cluster will be stopped to preserve the validation point."
} finally {
    if ($started) {
        & (Join-Path $pg "pg_ctl.exe") -D $data -m fast -w stop
        if ($LASTEXITCODE -ne 0) { Write-Warning "Could not stop work cluster: check local pg_ctl state manually." }
    }
}
