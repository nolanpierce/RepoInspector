from dotenv import load_dotenv
import os

load_dotenv()

CONFIG = {
    "VULTR_API_KEY": os.getenv("VULTR_API_KEY"),
    "VULTR_ENDPOINT": os.getenv("VULTR_ENDPOINT"),
    "VULTR_MODEL": os.getenv("VULTR_MODEL"),
}

missing = [k for k, v in CONFIG.items() if not v]
if missing:
    raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

vultr_token = CONFIG["VULTR_API_KEY"]
vultr_base  = CONFIG["VULTR_ENDPOINT"]
vultr_model = CONFIG["VULTR_MODEL"]
