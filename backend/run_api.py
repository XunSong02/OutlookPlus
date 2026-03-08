from pathlib import Path

from outlookplus_backend.utils.dotenv import load_dotenv


# Load env from OutlookPlus/backend/.env regardless of current working directory.
# Use override=True so editing .env reliably changes runtime behavior.
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from outlookplus_backend.api.app import create_app

app = create_app()

if __name__ == "__main__":
    import os

    import uvicorn

    # Minimal diagnostics (no secrets)
    print(
        "[api] starting"
        f" host={os.getenv('OUTLOOKPLUS_API_HOST', '127.0.0.1')}"
        f" port={os.getenv('OUTLOOKPLUS_API_PORT', '8000')}"
        f" auth_mode={os.getenv('OUTLOOKPLUS_AUTH_MODE', 'A')}"
        f" db_path={os.getenv('OUTLOOKPLUS_DB_PATH', 'data/outlookplus.db')}"
    )

    host = os.getenv("OUTLOOKPLUS_API_HOST", "127.0.0.1")
    port = int(os.getenv("OUTLOOKPLUS_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
