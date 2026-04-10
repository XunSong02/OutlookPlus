from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from outlookplus_backend.utils.file_lock import interprocess_lock


@dataclass(frozen=True)
class AttachmentFileStore:
    attachments_dir: str

    def write_bytes(self, *, user_id: str, email_id: int, attachment_id: int, content_type: str, data: bytes) -> str:
        # Deterministic path; content_type included for readability.
        safe_ct = content_type.replace("/", "_")
        rel = os.path.join(user_id, str(email_id), f"{attachment_id}.{safe_ct}.bin")
        dst = os.path.join(self.attachments_dir, rel)
        Path(os.path.dirname(dst)).mkdir(parents=True, exist_ok=True)

        lock_path = dst + ".lock"
        tmp_path = dst + ".tmp"

        with interprocess_lock(lock_path):
            with open(tmp_path, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, dst)

        return dst
