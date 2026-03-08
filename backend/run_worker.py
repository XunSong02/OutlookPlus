import os
import time
from pathlib import Path
import traceback

from outlookplus_backend.wiring import build_worker
from outlookplus_backend.utils.dotenv import load_dotenv
from outlookplus_backend.imap.client import MailboxError


def main() -> None:
    # Load env from OutlookPlus/backend/.env regardless of current working directory.
    # Use override=True so editing .env reliably changes runtime behavior.
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

    # Immediate startup diagnostics (no secrets).
    imap_host = os.getenv("OUTLOOKPLUS_IMAP_HOST")
    imap_user = os.getenv("OUTLOOKPLUS_IMAP_USERNAME")
    imap_pass = os.getenv("OUTLOOKPLUS_IMAP_PASSWORD") or ""
    imap_pass_set = bool(imap_pass)
    imap_pass_len = len(imap_pass)
    imap_folder = os.getenv("OUTLOOKPLUS_IMAP_FOLDER", "INBOX")
    imap_port = os.getenv("OUTLOOKPLUS_IMAP_PORT", "993")
    db_path = os.getenv("OUTLOOKPLUS_DB_PATH", "data/outlookplus.db")
    auth_mode = os.getenv("OUTLOOKPLUS_AUTH_MODE", "A")
    print(
        "[worker] starting"
        f" cwd={Path.cwd()}"
        f" auth_mode={auth_mode}"
        f" db_path={db_path}"
        f" imap_host={'set' if imap_host else 'missing'}"
        f" imap_user={'set' if imap_user else 'missing'}"
        f" imap_password={'set' if imap_pass_set else 'missing'}"
        f" imap_password_len={imap_pass_len if imap_pass_set else 0}"
        f" imap_folder={imap_folder}"
        f" imap_port={imap_port}",
        flush=True,
    )

    user_id = os.getenv("OUTLOOKPLUS_WORKER_USER_ID")
    if not user_id:
        raise SystemExit("Set OUTLOOKPLUS_WORKER_USER_ID")

    print(f"[worker] user_id={user_id}", flush=True)

    worker = build_worker()
    poll_seconds = float(os.getenv("OUTLOOKPLUS_WORKER_POLL_SECONDS", "15"))

    while True:
        try:
            ingested = worker.run_once(user_id=user_id)
            if ingested > 0:
                print(f"[worker] ingested={ingested}", flush=True)
            if ingested == 0:
                print("[worker] no new messages", flush=True)
                time.sleep(poll_seconds)
        except MailboxError as e:
            print(f"[worker] IMAP error: {e}", flush=True)
            time.sleep(poll_seconds)
        except Exception:
            print("[worker] unexpected error:\n" + traceback.format_exc(), flush=True)
            time.sleep(poll_seconds)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    main()
