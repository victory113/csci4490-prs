"""AI-assisted visit note categorization.

Implements AIR-01 and AIR-02: the suggestion is never stored without staff
acceptance, and a failure must not prevent the note from being saved.
"""

import os
import json
import urllib.request

CATEGORIES = ["Respiratory", "Digestive", "Musculoskeletal", "General/Other"]
TIMEOUT_SECONDS = 2
CONFIDENCE_THRESHOLD = 0.6

KEYWORDS = {
    "Respiratory": ["cough", "breath", "asthma", "wheeze", "chest", "congestion", "sinus"],
    "Digestive": ["stomach", "nausea", "vomit", "abdominal", "diarrhea", "appetite"],
    "Musculoskeletal": ["back", "knee", "joint", "shoulder", "muscle", "sprain", "ankle"],
}


class AICategorizer:
    """Calls the external AI service, falling back to a keyword substitute."""

    def __init__(self, api_url=None, api_key=None):
        self.api_url = api_url or os.environ.get("PRS_AI_URL")
        self.api_key = api_key or os.environ.get("PRS_AI_KEY")
        self.last_source = None

    def suggest_category(self, note_text):
        """Return (category, confidence) or (None, 0.0) when no suggestion is available."""
        if self.api_url and self.api_key:
            try:
                payload = json.dumps({"text": note_text}).encode("utf-8")
                req = urllib.request.Request(
                    self.api_url, data=payload,
                    headers={"Content-Type": "application/json",
                             "Authorization": "Bearer " + self.api_key})
                resp = urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS)
                data = json.loads(resp.read().decode("utf-8"))
                category = data["category"]
                confidence = data["confidence"]
                if category in CATEGORIES and confidence >= CONFIDENCE_THRESHOLD:
                    self.last_source = "ai_service"
                    return category, confidence
                return None, 0.0
            except Exception:
                pass

        return self.keyword_fallback(note_text)

    def keyword_fallback(self, note_text):
        """TEMPORARY TEST SUBSTITUTE - not an AI model.

        Used when no AI service is configured or the service is unavailable.
        """
        self.last_source = "keyword_fallback"
        text = note_text.lower()
        for category in KEYWORDS:
            for word in KEYWORDS[category]:
                if word in text:
                    return category, 0.75
        return "General/Other", 0.6
