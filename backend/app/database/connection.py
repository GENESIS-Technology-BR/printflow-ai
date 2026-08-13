from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.config.settings import settings


database_url = settings.database_url
is_sqlite = database_url.startswith("sqlite")
is_postgresql = database_url.startswith("postgresql")


engine_options = {
    "pool_pre_ping": True,
}

if is_sqlite:
    engine_options["connect_args"] = {
        "check_same_thread": False,
    }

if is_postgresql:
    engine_options.update(
        {
            # Verifica a conexão antes de entregá-la para a aplicação.
            # Se estiver morta, o SQLAlchemy cria outra automaticamente.
            "pool_pre_ping": True,

            # Evita reutilizar por muito tempo conexões antigas.
            "pool_recycle": 300,

            # Tempo máximo aguardando conexão disponível no pool.
            "pool_timeout": 30,

            # Favorece conexões usadas recentemente.
            "pool_use_lifo": True,

            # Proteção adicional do psycopg2 para conexões de rede.
            "connect_args": {
                "connect_timeout": 10,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
        }
    )


engine = create_engine(
    database_url,
    **engine_options,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass
