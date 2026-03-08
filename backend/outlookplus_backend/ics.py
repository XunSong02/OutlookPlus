from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class IcsFields:
    method: Optional[str]
    summary: Optional[str]
    dtstart: Optional[str]
    dtend: Optional[str]
    organizer: Optional[str]
    location: Optional[str]


class IcsParseError(Exception):
    pass


class IcsExtractor:
    def extract(self, ics_bytes: bytes) -> Optional[IcsFields]:
        try:
            text = ics_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            raise IcsParseError(str(e))

        lines = text.splitlines()
        unfolded: list[str] = []
        for line in lines:
            if not line:
                continue
            if line.startswith(" ") or line.startswith("\t"):
                if unfolded:
                    unfolded[-1] += line.lstrip()
                else:
                    unfolded.append(line.lstrip())
            else:
                unfolded.append(line.strip("\r\n"))

        def get(prop: str) -> Optional[str]:
            prop_upper = prop.upper()
            for l in unfolded:
                if ":" not in l:
                    continue
                left, value = l.split(":", 1)
                name = left.split(";", 1)[0].strip().upper()
                if name == prop_upper:
                    v = value.strip()
                    return v if v else None
            return None

        # Return None when nothing meaningful is found.
        fields = IcsFields(
            method=get("METHOD"),
            summary=get("SUMMARY"),
            dtstart=get("DTSTART"),
            dtend=get("DTEND"),
            organizer=get("ORGANIZER"),
            location=get("LOCATION"),
        )

        if not any(
            [
                fields.method,
                fields.summary,
                fields.dtstart,
                fields.dtend,
                fields.organizer,
                fields.location,
            ]
        ):
            return None

        return fields
