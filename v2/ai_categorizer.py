"""AI-assisted visit note categorization (prs.ai_integration).

This module is the only place that contacts the external AI provider, which
is what keeps an AI failure away from the record-handling components
(AIR-01, AIR-02).

It returns a CategorySuggestion rather than printing or storing anything. The
caller decides what to show, and only a staff member can cause a category to
be stored.
"""

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

CATEGORIES = ("Respiratory", "Digestive", "Musculoskeletal", "General/Other")
TIMEOUT_SECONDS = 2
CONFIDENCE_THRESHOLD = 0.6

_KEYWORDS = {
    "Respiratory": ("cough", "breath", "asthma", "wheeze", "chest", "congestion", "sinus"),
    "Digestive": ("stomach", "nausea", "vomit", "abdominal", "diarrhea", "appetite"),
    "Musculoskeletal": ("back", "knee", "joint", "shoulder", "muscle", "sprain", "ankle"),
}


class CategorySuggestion:
    """The outcome of a categorization attempt.

    `available` is False whenever no suggestion may be shown, which covers a
    timeout, a transport error, a category outside the fixed list, and
    confidence below the threshold (AIR-02).
    """

    def __init__(self, category=None, confidence=0.0, source="none", reason=""):
        self.category = category
        self.confidence = confidence
        self.source = source
        self.reason = reason

    @property
    def available(self):
        return self.category is not None

    @classmethod
    def none(cls, reason):
        return cls(None, 0.0, "none", reason)

    def __repr__(self):
        return f"CategorySuggestion({self.category!r}, {self.confidence!r}, {self.source!r})"


class AICategorizer:
    """Adapter for the external categorization service (realises IAICategorizer)."""

    def __init__(self, api_url=None, api_key=None, timeout=TIMEOUT_SECONDS,
                 threshold=CONFIDENCE_THRESHOLD):
        self.api_url = api_url if api_url is not None else os.environ.get("PRS_AI_URL")
        self.api_key = api_key if api_key is not None else os.environ.get("PRS_AI_KEY")
        self.timeout = timeout
        self.threshold = threshold

    @property
    def service_configured(self):
        return bool(self.api_url and self.api_key)

    def suggest_category(self, note_text):
        """Never raises. Returns a CategorySuggestion, possibly unavailable."""
        if not self.service_configured:
            return self._keyword_substitute(note_text)
        try:
            return self._call_service(note_text)
        except urllib.error.URLError as exc:
            logger.warning("AI categorization transport failure: %s", exc)
            return CategorySuggestion.none("AI service unavailable")
        except (TimeoutError, OSError) as exc:
            logger.warning("AI categorization timed out: %s", exc)
            return CategorySuggestion.none("AI service timed out")
        except (ValueError, KeyError) as exc:
            logger.warning("AI categorization returned an unusable response: %s", exc)
            return CategorySuggestion.none("AI response could not be read")

    def _call_service(self, note_text):
        # Only the note text is sent. No Patient ID, name, or other identifier.
        payload = json.dumps({"text": note_text}).encode("utf-8")
        request = urllib.request.Request(
            self.api_url, data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        category = data["category"]
        confidence = float(data["confidence"])
        if category not in CATEGORIES:
            return CategorySuggestion.none("AI returned a category outside the permitted list")
        if confidence < self.threshold:
            return CategorySuggestion.none("AI confidence below threshold")
        return CategorySuggestion(category, confidence, "ai_service")

    def _keyword_substitute(self, note_text):
        """TEMPORARY TEST SUBSTITUTE - this is not an AI model.

        Used only when no AI service is configured, so the application can be
        demonstrated without a provider. Clearly reported as its own source so
        it is never mistaken for a model result.
        """
        text = note_text.lower()
        for category, words in _KEYWORDS.items():
            if any(word in text for word in words):
                return CategorySuggestion(category, 0.75, "keyword_substitute")
        return CategorySuggestion("General/Other", 0.6, "keyword_substitute")
