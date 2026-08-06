from pathlib import Path
import json

CONFIG_FILE = Path.home() / ".printflow_agent.json"

DEFAULT_API = "https://printflow-api-genesis.onrender.com"


def load():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())

    return {
        "token": "",
        "api": DEFAULT_API
    }


def save(data):
    CONFIG_FILE.write_text(
        json.dumps(data, indent=4)
    )
