import json
import os
import uuid

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        config = {
            "client_guid": str(uuid.uuid4()),
            "client_server": "ws://127.0.0.1:8000",
            "connections": []
        }
        save_config(config)
    else:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    return config

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
