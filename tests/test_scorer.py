"""Tests for the scoring engine and platform rules."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scorer import ContentScorer
from services.platform_rules import PLATFORMS, get_platform_spec


def test_scoring_basic():
    text = "Email marketing delivers $36 for every $1 spent. Here are 10 tips to boost your campaigns."
    score = ContentScorer.score_text(text, "linkedin")
    assert 0 <= score.overall <= 100
    assert score.grade in ["A+", "A", "B", "C", "D", "F"]
    print(f"[PASS] Basic scoring: {score.overall} ({score.grade})")
    print(f"  Readability: {score.readability}")
    print(f"  Engagement: {score.engagement}")
    print(f"  Sentiment: {score.sentiment}")


def test_empty_content():
    score = ContentScorer.score_text("", "linkedin")
    assert score.overall == 0
    assert "Empty content" in score.issues
    print("[PASS] Empty content handled")


def test_long_content():
    text = "This is a very long piece of content. " * 200
    score = ContentScorer.score_text(text, "twitter")
    assert score.platform_fit < 50
    print(f"[PASS] Long content on Twitter: platform_fit={score.platform_fit}")


def test_hook_scoring():
    good_hook = "Nobody tells you this about email marketing..."
    bad_hook = "I think that maybe email marketing could potentially be useful."
    s1 = ContentScorer._score_hook(good_hook, [], [])
    s2 = ContentScorer._score_hook(bad_hook, [], [])
    assert s1 > s2
    print(f"[PASS] Hook scoring: good={s1:.0f} vs bad={s2:.0f}")


def test_cta_detection():
    with_cta = "Great tips for marketing. What do you think? Drop a comment below."
    without_cta = "Marketing is important for businesses today."
    s1 = ContentScorer._score_cta(with_cta, "linkedin", [], [])
    s2 = ContentScorer._score_cta(without_cta, "linkedin", [], [])
    assert s1 > s2
    print(f"[PASS] CTA scoring: with={s1:.0f} vs without={s2:.0f}")


def test_platform_specs():
    for name, spec in PLATFORMS.items():
        assert "max_chars" in spec
        assert "tone" in spec
        assert "best_practices" in spec
        assert len(spec["best_practices"]) > 0
    print(f"[PASS] All {len(PLATFORMS)} platform specs valid")


def test_engagement_heuristics():
    text_with_numbers = "5 proven ways to increase conversions by 200% using $0 budget."
    text_plain = "There are some ways to increase conversions."
    s1 = ContentScorer._score_engagement(text_with_numbers, [], [])
    s2 = ContentScorer._score_engagement(text_plain, [], [])
    assert s1 > s2
    print(f"[PASS] Engagement heuristics: numbers={s1:.0f} vs plain={s2:.0f}")


if __name__ == "__main__":
    print("=== AI Content Multiplexer - Tests ===\n")
    test_scoring_basic()
    test_empty_content()
    test_long_content()
    test_hook_scoring()
    test_cta_detection()
    test_platform_specs()
    test_engagement_heuristics()
    print("\n=== All tests passed! ===")
