import asyncio
import json

from agent.python.snmp.engine import collect_printer_intelligence


IP = "10.2.0.124"


async def main():
    print("=" * 70)
    print("PRINTFLOW - DIAGNOSTICO DO MOTOR SNMP")
    print(f"Impressora de referencia: {IP}")
    print("=" * 70)

    try:
        resultado = await collect_printer_intelligence(
            ip_address=IP,
            community="public",
            timeout=3.0,
            retries=1,
        )

        print("\nRESULTADO COMPLETO:\n")
        print(
            json.dumps(
                resultado,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )

    except Exception as erro:
        print("\nERRO DURANTE O TESTE:")
        print(repr(erro))

    print("\n" + "=" * 70)
    print("FIM DO DIAGNOSTICO")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
