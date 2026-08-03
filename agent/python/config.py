import os

API_URL = os.getenv(
    "PRINTFLOW_API_URL",
    "https://printflow-api-3uwr.onrender.com"
).rstrip("/")

PRINTER_IP = os.getenv("PRINTFLOW_PRINTER_IP", "10.2.0.124")
PRINTER_NAME = os.getenv("PRINTFLOW_PRINTER_NAME", "HP Laser MFP 432")
MANUFACTURER = os.getenv("PRINTFLOW_MANUFACTURER", "HP")
MODEL = os.getenv("PRINTFLOW_MODEL", "Laser MFP 432")
TIMEOUT = int(os.getenv("PRINTFLOW_TIMEOUT", "8"))
