"""Carga opt-in e idempotente de impressoras ficticias no SQLite isolado SupriTech.

Executar a partir da raiz do repositorio com:
 DATABASE_URL=sqlite:////tmp/talvoa_mvp_demo_20261030.db ENVIRONMENT=development \
 TALVOA_DEMO_SEED=YES python -m scripts.seed_supritech_demo_printers

Usa reflexao SQLAlchemy Core: nao depende do registro de modelos ORM.
Nao cria tabelas, contas ou empresas; nao acessa ambientes remotos.
"""
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

EXPECTED_DB = "/tmp/talvoa_mvp_demo_20261030.db"
if os.environ.get("TALVOA_DEMO_SEED") != "YES":
    raise SystemExit("BLOQUEADO: defina TALVOA_DEMO_SEED=YES")
if os.environ.get("ENVIRONMENT") != "development":
    raise SystemExit("BLOQUEADO: ENVIRONMENT deve ser development")
if os.environ.get("DATABASE_URL") != "sqlite:///" + EXPECTED_DB:
    raise SystemExit("BLOQUEADO: DATABASE_URL diferente do SQLite isolado")
if not Path(EXPECTED_DB).is_file() or Path(EXPECTED_DB).is_symlink():
    raise SystemExit("BLOQUEADO: banco isolado inexistente ou link simbolico")

from sqlalchemy import MetaData, Table, create_engine, select

engine = create_engine(os.environ["DATABASE_URL"])
if engine.dialect.name != "sqlite" or engine.url.database != EXPECTED_DB:
    raise SystemExit("BLOQUEADO: engine nao aponta para o banco isolado")

DEMO = (
    ("192.0.2.11", "DEMO - IMPRESSORA RH", "RH", "HP", "LaserJet Pro", 12840, "DEMO-RH-001"),
    ("192.0.2.12", "DEMO - IMPRESSORA FISCAL", "FISCAL", "Ricoh", "IM C3000", 38420, "DEMO-FIS-002"),
    ("192.0.2.13", "DEMO - IMPRESSORA ENGENHARIA", "ENGENHARIA", "Canon", "imageRUNNER", 9120, "DEMO-ENG-003"),
)
metadata = MetaData()
try:
    users = Table("users_v2", metadata, autoload_with=engine)
    companies = Table("companies_v2", metadata, autoload_with=engine)
    partners = Table("partners", metadata, autoload_with=engine)
    memberships = Table("partner_memberships", metadata, autoload_with=engine)
    printers = Table("printers", metadata, autoload_with=engine)
except Exception as exc:
    raise SystemExit(f"BLOQUEADO: estrutura de demo incompleta: {type(exc).__name__}") from exc

with engine.begin() as conn:
    user = conn.execute(select(users).where(users.c.username == "supritech_demo")).mappings().one_or_none()
    if not user:
        raise SystemExit("BLOQUEADO: usuario demo inexistente")
    company = conn.execute(select(companies).where(companies.c.id == user["company_id"])).mappings().one_or_none()
    if not company or company["name"] != "SUPRITECH DEMONSTRACAO":
        raise SystemExit("BLOQUEADO: empresa demo inesperada")
    membership = conn.execute(select(memberships).where(
        memberships.c.user_id == user["id"],
        memberships.c.active.is_(True),
        memberships.c.role == "partner_admin",
    )).mappings().one_or_none()
    if not membership or company["partner_id"] != membership["partner_id"]:
        raise SystemExit("BLOQUEADO: vinculo de parceiro invalido")
    partner = conn.execute(select(partners).where(partners.c.id == membership["partner_id"])).mappings().one_or_none()
    if not partner or partner["name"] != "SUPRITECH DEMONSTRACAO":
        raise SystemExit("BLOQUEADO: parceiro inesperado")

    created = 0
    for ip, name, sector, manufacturer, model, pages, serial in DEMO:
        existing = conn.execute(select(printers).where(
            printers.c.company_id == company["id"], printers.c.ip == ip,
        )).mappings().one_or_none()
        if existing:
            if existing["source"] != "demo" or existing["serial"] != serial:
                raise SystemExit(f"BLOQUEADO: IP {ip} ja utilizado por outro registro")
            continue
        conn.execute(printers.insert().values(
            company_id=company["id"], uuid=str(uuid4()), ip=ip, name=name, custom_name=name,
            sector_name=sector, manufacturer=manufacturer, model=model,
            page_count=pages, serial=serial, source="demo",
            status="online", active=True, page_count_source="demo",
            page_count_confirmed=False, serial_source="demo",
            serial_confirmed=False, cost_model="per_page",
            last_seen=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc),
        ))
        created += 1
print(f"DEMO SUPRITECH: {created} impressoras ficticias criadas; {len(DEMO)} esperadas.")
print("ATENCAO: status e contadores simulados; nenhum Agent Windows foi testado.")
