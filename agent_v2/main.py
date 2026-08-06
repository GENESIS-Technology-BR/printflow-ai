from config.settings import load, save
from core.discovery import discover
from core.api import send_printer


config = load()

if not config["token"]:
    print()
    print("===================================")
    print("      PRINTFLOW AGENT V2")
    print("===================================")
    print()

    token = input("Cole o Token da Empresa: ").strip()

    config["token"] = token

    save(config)

    print("\nToken salvo.\n")


printers = discover()

print(f"\n{len(printers)} impressora(s) encontrada(s).\n")

for printer in printers:

    print(f"Enviando {printer['ip']}...")

    send_printer(
        config["api"],
        config["token"],
        printer
    )

print()

print("Finalizado.")
