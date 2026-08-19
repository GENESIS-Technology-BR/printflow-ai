from __future__ import annotations


# PRINTFLOW_C1_PRINTER_INTELLIGENCE_HOOK
from intelligence.agent_cycle_integration import install_agent_cycle_hook
install_agent_cycle_hook()

import argparse
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(CURRENT_DIR),
    )


from config.settings import AgentSettings
from core.logger import configure_logger
from core.scheduler import AgentScheduler
from core.service import PrintflowAgentService


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PRINTFLOW Agent Core — "
            "Discovery, SNMP e Inventário"
        )
    )

    parser.add_argument(
        "--network",
        action="append",
        default=[],
        help=(
            "Rede adicional autorizada. "
            "Exemplo: --network 10.2.0.0/24"
        ),
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help=(
            "Mantém o Agent ativo e executa "
            "novos ciclos automaticamente."
        ),
    )

    return parser.parse_args()


def print_banner(
    settings: AgentSettings,
) -> None:
    print()
    print("=" * 72)
    print(
        f"{settings.agent_name.upper()} "
        f"v{settings.agent_version}"
    )
    print("=" * 72)
    print("Discovery automático")
    print("Consulta SNMP")
    print("Inventário local")
    print("=" * 72)
    print()


def main() -> int:
    arguments = parse_arguments()
    settings = AgentSettings.load()

    print_banner(settings)

    logger = configure_logger(
        settings.logs_directory
    )

    service = PrintflowAgentService(
        settings=settings,
        logger=logger,
        manual_networks=arguments.network,
    )

    if not arguments.daemon:
        return service.run_cycle()

    logger.info(
        "Modo serviço ativado."
    )

    scheduler = AgentScheduler(
        interval_seconds=(
            settings.scan_interval_seconds
        ),
        logger=logger,
    )

    return scheduler.run(
        service.run_cycle
    )


if __name__ == "__main__":
    raise SystemExit(main())
