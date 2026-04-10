from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


class JsonValidationError(Exception):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise JsonValidationError(message)


def _as_float(x: Any, field: str) -> float:
    if isinstance(x, bool):
        raise JsonValidationError(f"{field} must be a number")
    if not isinstance(x, (int, float)):
        raise JsonValidationError(f"{field} must be a number")
    return float(x)


@dataclass(frozen=True)
class StrictJsonValidator:
    def _parse(self, raw_text: str) -> Any:
        try:
            return json.loads(raw_text)
        except Exception as e:
            raise JsonValidationError(f"Invalid JSON: {e}")

    def validate_meeting(self, *, raw_text: str) -> dict[str, Any]:
        obj = self._parse(raw_text)
        _require(isinstance(obj, dict), "Expected JSON object")
        _require("meetingRelated" in obj, "Missing meetingRelated")
        _require("confidence" in obj, "Missing confidence")
        _require("rationale" in obj, "Missing rationale")
        _require(isinstance(obj["meetingRelated"], bool), "meetingRelated must be boolean")
        confidence = _as_float(obj["confidence"], "confidence")
        _require(0.0 <= confidence <= 1.0, "confidence out of range")
        _require(isinstance(obj["rationale"], str), "rationale must be string")
        return {
            "meetingRelated": bool(obj["meetingRelated"]),
            "confidence": confidence,
            "rationale": str(obj["rationale"]),
        }

    def validate_reply_need(self, *, raw_text: str) -> dict[str, Any]:
        obj = self._parse(raw_text)
        _require(isinstance(obj, dict), "Expected JSON object")
        _require("label" in obj, "Missing label")
        _require("confidence" in obj, "Missing confidence")
        _require("reasons" in obj, "Missing reasons")
        label = obj["label"]
        _require(isinstance(label, str), "label must be string")
        _require(label in {"NEEDS_REPLY", "NO_REPLY_NEEDED", "UNSURE"}, "invalid label")
        confidence = _as_float(obj["confidence"], "confidence")
        _require(0.0 <= confidence <= 1.0, "confidence out of range")
        reasons = obj["reasons"]
        _require(isinstance(reasons, list), "reasons must be list")
        _require(1 <= len(reasons) <= 3, "reasons must be length 1..3")
        _require(all(isinstance(r, str) and r.strip() for r in reasons), "reasons must be non-empty strings")
        return {
            "label": label,
            "confidence": confidence,
            "reasons": [str(r) for r in reasons],
        }

    def validate_email_analysis(self, *, raw_text: str) -> dict[str, Any]:
        obj = self._parse(raw_text)
        _require(isinstance(obj, dict), "Expected JSON object")
        _require("category" in obj, "Missing category")
        _require("sentiment" in obj, "Missing sentiment")
        _require("summary" in obj, "Missing summary")
        _require("suggestedActions" in obj, "Missing suggestedActions")

        category = obj["category"]
        _require(isinstance(category, str), "category must be string")
        _require(category in {"Work", "Personal", "Finance", "Social", "Promotions", "Urgent"}, "invalid category")

        sentiment = obj["sentiment"]
        _require(isinstance(sentiment, str), "sentiment must be string")
        _require(sentiment in {"positive", "neutral", "negative"}, "invalid sentiment")

        summary = obj["summary"]
        _require(isinstance(summary, str), "summary must be string")

        actions = obj["suggestedActions"]
        _require(isinstance(actions, list), "suggestedActions must be list")
        _require(len(actions) == 3, "suggestedActions must be length 3")

        out_actions: list[dict[str, Any]] = []
        for i, a in enumerate(actions):
            _require(isinstance(a, dict), f"suggestedActions[{i}] must be object")
            _require("kind" in a, f"suggestedActions[{i}] missing kind")
            _require("text" in a, f"suggestedActions[{i}] missing text")
            kind = a["kind"]
            _require(isinstance(kind, str), f"suggestedActions[{i}].kind must be string")
            _require(kind in {"reply_draft", "suggestion"}, f"suggestedActions[{i}].kind invalid")
            text = a["text"]
            _require(isinstance(text, str) and text.strip(), f"suggestedActions[{i}].text must be non-empty string")

            if kind == "reply_draft":
                _require("draft" in a, f"suggestedActions[{i}] missing draft")
                draft = a["draft"]
                _require(isinstance(draft, dict), f"suggestedActions[{i}].draft must be object")
                for f in ("to", "subject", "body"):
                    _require(f in draft, f"suggestedActions[{i}].draft missing {f}")
                    _require(
                        isinstance(draft[f], str) and str(draft[f]).strip(),
                        f"suggestedActions[{i}].draft.{f} must be non-empty string",
                    )
                out_actions.append(
                    {"kind": "reply_draft", "text": str(text), "draft": {"to": str(draft["to"]), "subject": str(draft["subject"]), "body": str(draft["body"])}}
                )
            else:
                out_actions.append({"kind": "suggestion", "text": str(text), "draft": None})

        return {
            "category": category,
            "sentiment": sentiment,
            "summary": summary,
            "suggestedActions": out_actions,
        }

    def validate_ai_request(self, *, raw_text: str) -> dict[str, Any]:
        obj = self._parse(raw_text)
        _require(isinstance(obj, dict), "Expected JSON object")
        _require("responseText" in obj, "Missing responseText")
        _require(isinstance(obj["responseText"], str), "responseText must be string")
        _require(bool(obj["responseText"].strip()), "responseText must be non-empty")
        return {"responseText": str(obj["responseText"]) }
