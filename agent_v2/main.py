import time
from datetime import datetime

from config.settings import load, save
from core.discovery import discover
from core.api import send_printer

DEFAULT_INTERVAL_SECONDS = 300
RETRY_DELAY_SECONDS = 30


def log(message):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def ensure_token(config):
    if config.get("token"):
        return config

    print()
    print("===================================")
    print("      PRINTFLOW AGENT V2")
    print("===================================")
    print()

    config["token"] = input("Cole o Token da Empresa: ").strip()
    save(config)
    print("\nToken salvo.\n")
    return config


def run_collection(config):
    log("Iniciando ciclo de descoberta e coleta.")
    printers = discover()
    log(f"{len(printers)} impressora(s) encontrada(s).")

    sent = 0
    failed = 0

    for printer in printers:
        ip = printer.get("ip", "desconhecido")
        try:
            response = send_printer(config["api"], config["token"], printer)
            if response.ok:
                sent += 1
                log(f"Impressora {ip} sincronizada.")
            else:
                failed += 1
                log(f"Falha HTTP {response.status_code} ao sincronizar {ip}.")
        except Exception as exc:
            failed += 1
            log(f"Falha ao sincronizar {ip}: {exc}")

    log(f"Ciclo concluido: {sent} enviada(s), {failed} falha(s).")


def main():
    config = ensure_token(load())
    interval = int(config.get("interval_seconds", DEFAULT_INTERVAL_SECONDS))
    log(f"Agent iniciado. Intervalo de coleta: {interval}s.")

    while True:
        try:
            run_collection(config)
            log(f"Proxima coleta em {interval}s.")
            time.sleep(interval)
        except KeyboardInterrupt:
            log("Agent encerrado pelo operador.")
            break
        except Exception as exc:
            log(f"Erro no ciclo principal: {exc}. Nova tentativa em {RETRY_DELAY_SECONDS}s.")
            time.sleep(RETRY_DELAY_SECONDS)


if __name__ == "__main__":
    main()
