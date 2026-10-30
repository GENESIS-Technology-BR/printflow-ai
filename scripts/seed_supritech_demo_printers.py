"""Carga opt-in de impressoras FICTICIAS para o SQLite isolado da demo SupriTech.

Uso:
 DATABASE_URL=sqlite:////tmp/talvoa_mvp_demo_20261030.db ENVIRONMENT=development \
 TALVOA_DEMO_SEED=YES python scripts/seed_supritech_demo_printers.py

Nao cria usuarios, empresas ou tabelas. Nao altera dados de agentes reais.
"""
import os
from pathlib import Path

from sqlalchemy import select

EXPECTED_DB = "/tmp/talvoa_mvp_demo_20261030.db"
if os.environ.get("TALVOA_DEMO_SEED") != "YES":
    raise SystemExit("BLOQUEADO: defina TALVOA_DEMO_SEED=YES explicitamente")
if os.environ.get("ENVIRONMENT") != "development":
    raise SystemExit("BLOQUEADO: ENVIRONMENT deve ser development")
if os.environ.get("DATABASE_URL") != "sqlite:///" + EXPECTED_DB:
    raise SystemExit("BLOQUEADO: DATABASE_URL nao corresponde ao SQLite de demo")
if not Path(EXPECTED_DB).is_file():
    raise SystemExit("BLOQUEADO: arquivo SQLite de demo inexistente")

from backend.app.database.connection import SessionLocal, engine
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.partners.model import Partner, PartnerMembership
from backend.modules.printers.model import Printer

if engine.dialect.name != "sqlite" or engine.url.database != EXPECTED_DB:
    raise SystemExit("BLOQUEADO: engine nao aponta para o banco isolado")

DEMO = (
    ("192.0.2.11", "DEMO - IMPRESSORA RH", "RH", "HP", "LaserJet Pro", 12840, "DEMO-RH-001"),
    ("192.0.2.12", "DEMO - IMPRESSORA FISCAL", "FISCAL", "Ricoh", "IM C3000", 38420, "DEMO-FIS-002"),
    ("192.0.2.13", "DEMO - IMPRESSORA ENGENHARIA", "ENGENHARIA", "Canon", "imageRUNNER", 9120, "DEMO-ENG-003"),
)

with SessionLocal() as db:
    user = db.scalar(select(User).where(User.username == "supritech_demo"))
    if user is None:
        raise SystemExit("BLOQUEADO: usuario supritech_demo inexistente")
    company = db.get(Company, user.company_id)
    if company is None or company.name != "SUPRITECH DEMONSTRACAO":
        raise SystemExit("BLOQUEADO: empresa demo nao corresponde ao esperado")
    membership = db.scalar(select(PartnerMembership).where(
        PartnerMembership.user_id == user.id,
        PartnerMembership.active.is_(True),
    ))
    if membership is None or membership.role != "partner_admin" or company.partner_id != membership.partner_id:
        raise SystemExit("BLOQUEADO: vinculo de parceiro demo nao validado")
    partner = db.get(Partner, membership.partner_id)
    if partner is None or partner.name != "SUPRITECH DEMONSTRACAO":
        raise SystemExit("BLOQUEADO: parceiro nao corresponde ao esperado")

    created = 0
    for ip, name, sector, manufacturer, model, pages, serial in DEMO:
        existing = db.scalar(select(Printer).where(Printer.company_id == company.id, Printer.ip == ip))
        if existing:
            if existing.source != "demo" or existing.serial != serial:
                raise SystemExit(f"BLOQUEADO: IP {ip} ja utilizado por outro registro")
            continue
        db.add(Printer(
            company_id=company.id, ip=ip, name=name, custom_name=name,
            sector_name=sector, manufacturer=manufacturer, model=model,
            page_count=pages, serial=serial, source="demo",
            status="online", active=True, page_count_source="demo",
            serial_source="demo",
        ))
        created += 1
    db.commit()
    print(f"DEMO SUPRITECH: {created} impressoras ficticias criadas; {len(DEMO)} esperadas.")
    print("ATENCAO: status e contadores sao simulados, sem Agent Windows.")
