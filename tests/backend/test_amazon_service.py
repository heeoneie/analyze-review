"""Tests for Amazon mock ingestion and risk detection pipeline."""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.amazon_service import detect_risk_candidate, _classify_severity


class TestDetectRiskCandidate:
    """Tests for the fast keyword filter."""

    def test_detects_rash_keyword(self):
        assert detect_risk_candidate("I got a rash from this product") is True

    def test_detects_burn_keyword(self):
        assert detect_risk_candidate("This caused a chemical burn") is True

    def test_detects_lawsuit_keyword(self):
        assert detect_risk_candidate("I'm filing a lawsuit against them") is True

    def test_detects_fda_keyword(self):
        assert detect_risk_candidate("This violates FDA regulations") is True

    def test_detects_recall_keyword(self):
        assert detect_risk_candidate("This product should be recalled") is True

    def test_detects_hospital_keyword(self):
        assert detect_risk_candidate("I ended up in the hospital") is True

    def test_detects_fake_keyword(self):
        assert detect_risk_candidate("This is a fake product") is True

    def test_detects_scam_keyword(self):
        assert detect_risk_candidate("This is clearly a scam") is True

    def test_safe_review_returns_false(self):
        assert detect_risk_candidate("Great product, fast shipping") is False

    def test_average_review_returns_false(self):
        assert detect_risk_candidate("Okay quality, nothing special") is False

    def test_empty_text_returns_false(self):
        assert detect_risk_candidate("") is False

    def test_none_text_returns_false(self):
        assert detect_risk_candidate(None) is False

    def test_case_insensitive(self):
        assert detect_risk_candidate("FDA VIOLATION") is True
        assert detect_risk_candidate("RASH on my face") is True


class TestClassifySeverity:
    """Tests for the LLM-based severity classification."""

    def test_non_candidate_returns_safe(self):
        """Reviews without risk keywords skip LLM and return safe."""
        severity, label = _classify_severity("Great product, love it!")
        assert severity == 2.0
        assert label is None

    def test_llm_classification_called_for_candidate(self):
        """Risk candidate reviews are sent to LLM."""
        mock_classification = {
            "severity": 9.0,
            "risk_category": "Product Liability",
            "confidence": 0.95,
        }
        with patch("backend.services.amazon_service.classify_with_llm", return_value=mock_classification):
            severity, label = _classify_severity("I got a severe rash")
        assert severity == 9.0
        assert label == "Product Liability"

    def test_safe_category_returns_none_label(self):
        """LLM returning 'Safe' category results in None label."""
        mock_classification = {
            "severity": 2.0,
            "risk_category": "Safe",
            "confidence": 0.9,
        }
        with patch("backend.services.amazon_service.classify_with_llm", return_value=mock_classification):
            severity, label = _classify_severity("Minor rash but it went away")
        assert severity == 2.0
        assert label is None

    def test_llm_failure_falls_back_to_keywords(self):
        """When LLM fails, keyword fallback is used."""
        with patch("backend.services.amazon_service.classify_with_llm", side_effect=Exception("API Error")):
            severity, label = _classify_severity("I got a rash")
        assert severity == 9.0
        assert label == "Skin Irritation / Allergic Reaction"

    def test_llm_failure_with_no_keywords_returns_safe(self):
        """When LLM fails and no keywords match, return safe."""
        # This is a tricky case - the text has 'allergic' keyword so it will match
        # Let's use a text that passes detect_risk_candidate but has no _HIGH_RISK_KEYWORDS match
        with patch("backend.services.amazon_service.detect_risk_candidate", return_value=True):
            with patch("backend.services.amazon_service.classify_with_llm", side_effect=Exception("API Error")):
                # Using text without any _HIGH_RISK_KEYWORDS
                severity, label = _classify_severity("This product is a lie")  # 'lie' is in candidate but not in _HIGH_RISK_KEYWORDS
        assert severity == 2.0
        assert label is None
