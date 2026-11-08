#!/usr/bin/env python3
"""Linux mission #99 rehearsal. Synthetic data ONLY; no remote DB interface.

Requires a local Docker daemon, the pinned image already pulled, and cryptography.
No credentials, host mounts, published ports, persistent volumes or cloud APIs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone

from cryptography.exceptions import InvalidTag
from talvoa_secure_backup_windows import encrypt_dump
from talvoa_decrypt_backup_windows import decrypt_archive

IMAGE = "postgres:16-bookworm@sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9"
FIXTURE = b"""
CREATE TABLE orders (id serial PRIMARY KEY, code text UNIQUE NOT NULL);
CREATE TABLE items (id serial PRIMARY KEY, order_id integer REFERENCES orders(id), amount integer CHECK(amount > 0));
INSERT INTO orders(code) VALUES ('synthetic-a'), ('synthetic-b'), ('synthetic-c');
INSERT INTO items(order_id, amount) VALUES (1,10), (1,20), (2,30), (3,40), (3,50);
CREATE INDEX items_order_idx ON items(order_id);
CREATE VIEW order_totals AS SELECT order_id, sum(amount) AS amount FROM items GROUP BY order_id;
"""
INVENTORY = """
SELECT json_build_object(
 'tables', (SELECT count(*) FROM pg_tables WHERE schemaname='public'),
 'orders', (SELECT count(*) FROM orders), 'items', (SELECT count(*) FROM items),
 'amount', (SELECT sum(amount) FROM items),
 'data_hash', md5((SELECT string_agg(row(id,code)::text, ',' ORDER BY id) FROM orders)
                  || (SELECT string_agg(row(id,order_id,amount)::text, ',' ORDER BY id) FROM items)),
 'constraints', (SELECT string_agg(pg_get_constraintdef(oid), ',' ORDER BY conname)
                 FROM pg_constraint WHERE connamespace='public'::regnamespace),
 'indexes', (SELECT string_agg(indexdef, ',' ORDER BY indexname) FROM pg_indexes WHERE schemaname='public'),
 'view', pg_get_viewdef('order_totals'::regclass),
 'sequence', (SELECT last_value FROM orders_id_seq));
"""


def docker(*args: str, data: bytes | None = None, timeout: int = 60) -> bytes:
    # Never let inherited context/TLS selectors redirect to a remote daemon.
    env = {k: v for k, v in os.environ.items()
           if k not in {'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS',
                        'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'}}
    return subprocess.run(['docker', '--host=unix:///var/run/docker.sock', *args],
                          input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=env, check=True, timeout=timeout).stdout


def rehearse() -> dict:
    name = 'talvoa-m99-synthetic-' + secrets.token_hex(8)
    report = {'synthetic_only': True, 'image': IMAGE,
              'utc': datetime.now(timezone.utc).isoformat()}
    # Creation and removal are separate: cleanup covers failed start/readiness.
    cid = docker('create', '--name', name, '--label', 'talvoa.m99=synthetic',
                 '--pull=never', '--network=none', '--read-only', '--user=999:999',
                 '--cap-drop=ALL', '--security-opt=no-new-privileges',
                 '--memory=512m', '--cpus=1', '--pids-limit=128',
                 '--tmpfs', '/var/lib/postgresql/data:rw,noexec,nosuid,size=256m,uid=999,gid=999,mode=0700',
                 '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m,uid=999,gid=999,mode=0700',
                 '--entrypoint=bash', IMAGE, '-ceu',
                 'initdb -D /var/lib/postgresql/data --data-checksums --auth-local=trust --auth-host=reject > /tmp/initdb.log; '
                 'exec postgres -D /var/lib/postgresql/data -c listen_addresses= -c unix_socket_directories=/tmp').decode().strip()
    try:
        docker('start', cid)
        def execute(*args: str, data: bytes | None = None) -> bytes:
            return docker('exec', '-i', '--user=999:999', cid, *args, data=data)

        def sql(db: str, query: str) -> bytes:
            return execute('psql', '-X', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp',
                           '-U', 'postgres', '-d', db, '-At', data=query.encode())

        for attempt in range(60):
            try:
                sql('postgres', 'SELECT 1;')
                break
            except subprocess.CalledProcessError:
                if attempt == 59:
                    raise RuntimeError('Synthetic PostgreSQL did not become ready') from None
                time.sleep(0.5)
        config = json.loads(docker('inspect', cid))[0]
        if (config['HostConfig']['NetworkMode'] != 'none'
                or config['HostConfig']['PortBindings']
                or config['HostConfig']['Binds']):
            raise RuntimeError('Container isolation verification failed')
        if sql('postgres', 'SHOW listen_addresses;').strip():
            raise RuntimeError('Unexpected TCP listener')
        version = execute('pg_dump', '--version').decode().strip()
        if not version.startswith('pg_dump (PostgreSQL) 16.'):
            raise RuntimeError('PostgreSQL 16 is required')
        sql('postgres', 'CREATE DATABASE m99_source; CREATE DATABASE m99_restored;')
        sql('m99_source', FIXTURE.decode())
        expected = json.loads(sql('m99_source', INVENTORY))
        dump = execute('pg_dump', '-h', '/tmp', '-U', 'postgres', '-Fc', 'm99_source')
        with tempfile.TemporaryDirectory(prefix='m99-synthetic-') as td:
            folder = Path(td)  # TemporaryDirectory uses mode 0700 on Linux.
            plain, archive, recovered = (folder / n for n in ('source.dump', 'synthetic.aesgcm', 'restored.dump'))
            plain.write_bytes(dump)
            phrase = secrets.token_urlsafe(48)  # Synthetic ephemeral key; never logged.
            encrypt_dump(plain, archive, phrase)
            encrypted = archive.read_bytes()
            for wrong_key, corrupt in ((True, False), (False, True)):
                candidate = folder / 'negative.aesgcm'
                candidate.write_bytes(encrypted[:-1] + bytes([encrypted[-1] ^ 1]) if corrupt else encrypted)
                rejected = folder / 'rejected.dump'
                try:
                    decrypt_archive(candidate, 'synthetic-wrong-key' if wrong_key else phrase, rejected)
                except InvalidTag:
                    pass
                else:
                    raise RuntimeError('Unauthenticated ciphertext was accepted')
                if rejected.exists() or rejected.with_suffix('.dump.partial').exists():
                    raise RuntimeError('Failed decryption left plaintext')
            decrypt_archive(archive, phrase, recovered)
            if recovered.read_bytes() != dump:
                raise RuntimeError('Decrypted dump differs from source')
            execute('pg_restore', '--list', data=recovered.read_bytes())
            execute('pg_restore', '--exit-on-error', '--single-transaction', '--no-owner', '--no-acl',
                    '-h', '/tmp', '-U', 'postgres', '-d', 'm99_restored', data=recovered.read_bytes())
            actual = json.loads(sql('m99_restored', INVENTORY))
            if actual != expected or (actual['tables'], actual['orders'], actual['items'], actual['amount']) != (2, 3, 5, 150):
                raise RuntimeError('Restored inventory/data differs from synthetic source')
            # Sequence and foreign key behavior after restore, beyond row counts.
            if sql('m99_restored', "INSERT INTO orders(code) VALUES ('synthetic-d') RETURNING id;").splitlines()[0] != b'4':
                raise RuntimeError('Restored sequence failed')
            try:
                sql('m99_restored', 'INSERT INTO items(order_id,amount) VALUES (999,1);')
            except subprocess.CalledProcessError:
                pass
            else:
                raise RuntimeError('Restored foreign key did not reject invalid row')
            report.update(pg_dump=version, dump_bytes=len(dump),
                          dump_sha256=hashlib.sha256(dump).hexdigest(),
                          encrypted_bytes=len(encrypted),
                          encrypted_sha256=hashlib.sha256(encrypted).hexdigest(),
                          tables=2, rows=8, restore='PASS', inventory_equal=True,
                          wrong_key_rejected=True, tamper_rejected=True,
                          sequence_verified=True, foreign_key_verified=True,
                          network='none', tcp_listener=False)
        report['temporary_files_removed'] = not folder.exists()
    finally:
        docker('rm', '-f', '-v', cid)
    report['container_removed'] = True
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic-only', required=True, action='store_true')
    parser.parse_args()
    def terminate(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, terminate)
    print(json.dumps(rehearse(), indent=2))


if __name__ == '__main__':
    main()
