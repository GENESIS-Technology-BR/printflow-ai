#!/usr/bin/env python3
"""Read-only portable recovery preflight for TALVOA mission #99.

No credentials, PostgreSQL connections, decryptions, network requests, or
file mutations. Works in any Windows user profile with a synchronized
OneDrive account or a manually supplied file path.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import sys

BACKUP_NAME = "supritech-20261104T175511Z-656276385a8791e2.dump.aesgcm"
BACKUP_SHA256 = "55f4ea0533895c1ae4e7f827b02e58b93145b8fd86d319ea53a98de45628de4a"
BACKUP_SIZE = 55687


def candidates(explicit: str | None, home: Path, environ: dict[str, str]) -> list[Path]:
    if explicit:
        return [Path(explicit).expanduser()]
    folders = []
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        if environ.get(var):
            folders.append(Path(environ[var]))
    folders.extend([home / "OneDrive", home / "TALVOA_Backups"])
    # Deduplicate without assuming user-specific directory names.
    files = []
    seen = set()
    for root in folders:
        for target in (root / "TALVOA-Backups" / BACKUP_NAME, root / BACKUP_NAME):
            key = str(target).casefold()
            if key not in seen:
                seen.add(key)
                files.append(target)
    return files


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assess_file(path: Path) -> list[str]:
    problems = []
    if not path.is_file():
        return ["Arquivo nao encontrado (sincronize/baixe o OneDrive no perfil atual)"]
    if path.is_symlink():
        problems.append("Arquivo e um link simbolico; use uma copia local regular")
    if path.stat().st_size != BACKUP_SIZE:
        problems.append("Tamanho diferente do backup auditado")
    if checksum(path).lower() != BACKUP_SHA256:
        problems.append("SHA-256 diferente do backup auditado")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Missao #99: preflight OFFLINE do backup AES-GCM")
    parser.add_argument("--backup", help="Caminho local do arquivo .aesgcm ja baixado")
    args = parser.parse_args()
    found = [p for p in candidates(args.backup, Path.home(), dict(os.environ)) if p.is_file()]
    if not found:
        print("BLOQUEADO: backup nao encontrado no perfil Windows atual.")
        print("Baixe da sua pasta OneDrive/TALVOA-Backups ou indique --backup com caminho local.")
        print("NENHUMA restauracao, rede ou acesso ao banco foi executado.")
        return 2
    for path in found:
        problems = assess_file(path)
        if not problems:
            print("BACKUP LOCAL VALIDADO (tamanho e SHA-256).")
            print("Caminho:", path)
            print("Bytes:", BACKUP_SIZE)
            print("SHA-256:", BACKUP_SHA256)
            print("Proximo passo: preparar PostgreSQL 16 LOCAL e entrada secreta oculta.")
            print("A restauracao ainda NAO foi executada. Nao usar Render/Neon.")
            return 0
        print("REJEITADO:", path)
        for problem in problems:
            print(" -", problem)
    return 3


if __name__ == "__main__":
    sys.exit(main())
