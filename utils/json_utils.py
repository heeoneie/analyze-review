"""JSON parsing helpers for model responses."""

import json
import logging
import re

logger = logging.getLogger(__name__)


def extract_json_from_text(text):
    """Extract JSON content from a response string with basic sanitization."""
    match = re.search(r"```(?:json)?\n(.*?)\n```", text, re.S | re.I)
    if match:
        candidate = match.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
        else:
            candidate = text.strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        logger.warning("Initial JSON parse failed: %s; raw response: %s", exc, text)
        repaired = candidate.replace("{{", "{").replace("}}", "}")
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            logger.error("Repaired JSON still invalid. Returning empty object.")
            return {}
