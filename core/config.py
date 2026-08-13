import os
import json
from core.logger import get_logger

logger = get_logger(__name__)

CONFIG_DIR = "settings"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

class ConfigManager:
    def __init__(self):
        self.config = {
            "theme": "dark",
            "default_export_path": os.path.join(os.path.expanduser("~"), "Documents", "KDP_Projects")
        }
        self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
            
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        else:
            self.save_config()

    def save_config(self):
        try:
            if not os.path.exists(CONFIG_DIR):
                os.makedirs(CONFIG_DIR)
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

config = ConfigManager()
