#!/usr/bin/env python3
"""Mission #99: restore an existing TALVOA AES-GCM backup to a disposable LOCAL PG16.

Interactive, Windows-only, no Render/Neon credentials, no production endpoints.
Requires PostgreSQL 16 *server and client* binaries and cryptography.
All subprocess output is sanitized; plaintext and local cluster are ephemeral.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile

from talvoa_secure_backup_windows import (
    read_secret, verify_private_windows_acl,
)
from talvoa_decrypt_backup_windows import decrypt_archive

EXPECTED_NAME = "supritech-20261104T175511Z-656276385a8791e2.dump.aesgcm"
EXPECTED_SHA = "55f4ea0533895c1ae4e7f827b02e58b93145b8fd86d319ea53a98de45628de4a"
EXPECTED_BYTES = 55687
PORT = 60439
DB = "talvoa_restore_m99"
USER = "talvoa_restore_m99_owner"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def validate_archive(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Arquivo ausente ou link simbolico: use download local regular")
    if path.name != EXPECTED_NAME:
        raise RuntimeError("Nome do arquivo diferente do backup auditado")
    if path.stat().st_size != EXPECTED_BYTES or sha256(path).lower() != EXPECTED_SHA:
        raise RuntimeError("Backup nao corresponde ao tamanho/SHA-256 auditado")


def pg_binaries(pg_bin: str | None) -> dict[str, Path]:
    roots = [Path(pg_bin)] if pg_bin else []
    for var in ("ProgramFiles", "ProgramW6432"):
        if os.environ.get(var):
            roots.append(Path(os.environ[var]) / "PostgreSQL" / "16" / "bin")
    roots.extend([Path("C:/Program Files/PostgreSQL/16/bin")])
    names = ("initdb", "pg_ctl", "pg_restore", "psql", "createdb")
    for base in roots:
        if all((base / (name + ".exe")).is_file() for name in names):
            return {name: (base / (name + ".exe")).resolve(strict=True) for name in names}
    found = {name: shutil.which(name + ".exe") for name in names}
    if all(found.values()):
        return {name: Path(value).resolve(strict=True) for name, value in found.items()}
    raise RuntimeError("PostgreSQL 16 bin nao encontrado; informe --pg-bin com caminho completo")


def run(argv: list[str], env: dict[str, str] | None = None, *, timeout: int = 120,
        stdout: bool = False) -> str:
    p = subprocess.run(argv, env=env, capture_output=True, text=True,
                       errors="replace", timeout=timeout, check=False)
    if p.returncode != 0:
        # Never echo stderr: external tools can echo parameters or environment.
        raise RuntimeError("Etapa local falhou; codigo de saida: " + str(p.returncode))
    return p.stdout if stdout else ""


def check_pg16(bins: dict[str, Path]) -> None:
    import re
    for name, path in bins.items():
        version = run([str(path), "--version"], timeout=20, stdout=True)
        if not re.search(r"\b16(?:\.|\b)", version):
            raise RuntimeError(f"{name} nao e PostgreSQL major 16")


def reserve_private_dir() -> Path:
    parent = Path.home() / "TALVOA_Restore_Private"
    if parent.is_symlink():
        raise RuntimeError("Diretorio base deve ser pasta fisica, nao link")
    parent.mkdir(exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="m99-", dir=parent))
    # For Windows, block inherited access before writing any sensitive data.
    if os.name != "nt":
        shutil.rmtree(folder)
        raise RuntimeError("Restauração local disponivel apenas no Windows")
    import ctypes
    import ctypes.wintypes
    # Use PowerShell only to derive current SID; it must not contain secrets.
    sid = run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
               "[Security.Principal.WindowsIdentity]::GetCurrent().User.Value"],
              stdout=True).strip()
    if not sid.startswith("S-1-"):
        raise RuntimeError("Nao foi possivel identificar SID do usuario Windows")
    # icacls edits ONLY the new temporary directory, never user folders.
    run(["icacls.exe", str(folder), "/inheritance:r"])
    run(["icacls.exe", str(folder), "/grant:r",
         f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F", "*S-1-5-32-544:(OI)(CI)F"])
    verify_private_windows_acl(folder)
    return folder


def verify_local_listener() -> None:
    # Fail if port already occupied, rather than risk attaching to another DB.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        if s.connect_ex(("127.0.0.1", PORT)) == 0:
            raise RuntimeError("Porta local ocupada; nenhuma restauracao executada")


def pg_env(password: str) -> dict[str, str]:
    # Clear inherited libpq overrides that could redirect to Render/Neon.
    e = {k: v for k, v in os.environ.items() if not k.upper().startswith("PG")}
    e.update({"PGHOST": "127.0.0.1", "PGPORT": str(PORT), "PGUSER": USER,
              "PGDATABASE": DB, "PGPASSWORD": password, "PGSSLMODE": "disable",
              "PGCONNECT_TIMEOUT": "5", "PGSERVICEFILE": os.devnull})
    return e


def count_restored_tables(psql: Path, env: dict[str, str]) -> tuple[int, int]:
    select_tables = (
        "SELECT quote_ident(schemaname)||'.'||quote_ident(tablename) "
        "FROM pg_catalog.pg_tables "
        "WHERE schemaname NOT IN ('pg_catalog','information_schema') "
        "ORDER BY schemaname, tablename"
    )
    rows = run([str(psql), "-X", "-w", "-q", "-t", "-A",
                "-h", "127.0.0.1", "-p", str(PORT), "-U", USER, "-d", DB,
                "-c", select_tables], env=env, stdout=True).splitlines()
    table_names = [name.strip() for name in rows if name.strip()]
    if not table_names:
        raise RuntimeError("Nenhuma tabela restaurada: NAO APROVADO")
    total = 0
    for name in table_names:
        result = run([str(psql), "-X", "-w", "-q", "-t", "-A",
                      "-h", "127.0.0.1", "-p", str(PORT), "-U", USER, "-d", DB,
                      "-c", "SELECT count(*) FROM " + name], env=env, stdout=True).strip()
        total += int(result)
    return len(table_names), total


def main() -> int:
    p = argparse.ArgumentParser(description="TALVOA M99: recuperacao real em banco LOCAL descartavel")
    p.add_argument("--backup", required=True, type=Path, help="Arquivo AESGCM baixado do OneDrive")
    p.add_argument("--pg-bin", help="Diretorio contendo PostgreSQL 16 initdb, pg_ctl, pg_restore e psql")
    args = p.parse_args()
    validate_archive(args.backup)
    bins = pg_binaries(args.pg_bin)
    check_pg16(bins)
    verify_local_listener()
    print("BACKUP VALIDADO: 55.687 bytes, SHA-256 correspondente.")
    print("Destino: SOMENTE 127.0.0.1:" + str(PORT) + "/" + DB)
    print("A restauracao ira criar e remover um cluster descartavel e plaintext temporario.")
    if input("Digite RESTAURAR LOCAL para autorizar: ").strip() != "RESTAURAR LOCAL":
        print("Cancelado sem executar.")
        return 2
    secret = read_secret("Frase secreta ORIGINAL do backup (oculta): ")
    if not secret:
        raise RuntimeError("Frase secreta vazia")
    folder = None
    cluster_started = False
    try:
        folder = reserve_private_dir()
        clear = folder / "source.dump"
        decrypt_archive(args.backup, secret, clear)
        secret = ""
        print("AES-256-GCM: autenticacao confirmada.")
        # Inspect archive locally before touching any database.
        run([str(bins["pg_restore"]), "--list", str(clear)], timeout=60)
        cluster = folder / "pgdata"
        cluster_password = secrets.token_urlsafe(32)
        pwfile = folder / "local-pg-password.txt"
        with pwfile.open("x", encoding="utf-8") as f:
            f.write(cluster_password + "\n")
        try:
            run([str(bins["initdb"]), "-D", str(cluster), "-U", USER,
                 "--encoding=UTF8", "--auth-host=scram-sha-256",
                 "--auth-local=scram-sha-256", "--pwfile", str(pwfile)], timeout=150)
        finally:
            pwfile.unlink(missing_ok=True)
        verify_local_listener()
        log = folder / "postgres-startup.log"
        run([str(bins["pg_ctl"]), "-D", str(cluster), "-l", str(log),
             "-o", f"-c listen_addresses=127.0.0.1 -c port={PORT} -c max_connections=10",
             "-w", "start"], timeout=90)
        cluster_started = True
        env = pg_env(cluster_password)
        run([str(bins["createdb"]), "-h", "127.0.0.1", "-p", str(PORT),
             "-U", USER, "-T", "template0", DB], env=env)
        run([str(bins["pg_restore"]), "--exit-on-error", "--single-transaction",
             "--no-owner", "--no-acl", "-h", "127.0.0.1", "-p", str(PORT),
             "-U", USER, "-d", DB, str(clear)], env=env, timeout=600)
        tables, rows = count_restored_tables(bins["psql"], env)
        print("RESTORE LOCAL: SUCESSO")
        print("Tabelas de usuario:", tables)
        print("Total de linhas (tabelas de usuario):", rows)
        print("Arquivo: ", args.backup.name)
        print("SHA-256:", EXPECTED_SHA)
        return 0
    finally:
        secret = ""
        if folder is not None:
            if cluster_started:
                try:
                    run([str(bins["pg_ctl"]), "-D", str(folder / "pgdata"),
                         "-m", "immediate", "-w", "stop"], timeout=45)
                    cluster_started = False
                except Exception:
                    print("ALERTA: cluster nao parou; dados temporarios podem permanecer!",
                          file=sys.stderr)
            if not cluster_started:
                try:
                    shutil.rmtree(folder)
                except Exception:
                    print("ALERTA: pasta de recuperacao nao pode ser removida; "
                          "proteja-a ate limpeza segura.", file=sys.stderr)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # Never print exception details that may contain a secret or data value.
        print("FALHA CONTROLADA:", type(exc).__name__, file=sys.stderr)
        sys.exit(1)
