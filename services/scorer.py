"""
Content Scorer — multi-dimensional NLP analysis.
Uses textstat for readability, vader for sentiment, and heuristics for engagement.
"""

import re
import math

try:
    import textstat
except ImportError:
    textstat = None

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
except ImportError:
    _vader = None

from core.models import ScoreBreakdown
from services.platform_rules import get_platform_spec


# ── Engagement power words ──

POSITIVE_WORDS = {
    "free", "proven", "instant", "new", "exclusive", "save", "easy",
    "guaranteed", "best", "fast", "quick", "simple", "powerful",
    "secret", "unlock", "boost", "growth", "increase", "results",
    "success", "win", "winning", " breakthrough", "remarkable",
}

NEGATIVE_WORDS = {
    "fail", "failure", "losing", "lost", "problem", "struggle",
    "difficult", "impossible", "never", "waste", "risk", "danger",
    "warning", "alert", "crisis", "panic",
}

POWER_PATTERNS = [
    (r"\d+%|\d+\%", 3),           # percentages get high weight
    (r"\$\d+", 3),                 # money amounts
    (r"\d+\s*(x|times)\b", 3),    # multipliers
    (r"\bhow to\b", 2),           # how-to hooks
    (r"\bwhy\b", 2),              # why hooks
    (r"\b\d+\s*(tips|ways|reasons|steps|secrets)\b", 3),  # listicle hooks
    (r"\b(you|your)\b", 1),       # second person
    (r"\?", 1),                    # questions
    (r"\b(because|here's why)\b", 2),  # curiosity gaps
]


class ContentScorer:
    """Scores content across multiple dimensions."""

    @staticmethod
    def score_text(text: str, platform: str = "linkedin") -> ScoreBreakdown:
        if not text or not text.strip():
            return ScoreBreakdown(overall=0, grade="F", issues=["Empty content"])

        issues = []
        suggestions = []

        readability = ContentScorer._score_readability(text, platform, issues, suggestions)
        sentiment = ContentScorer._score_sentiment(text)
        engagement = ContentScorer._score_engagement(text, issues, suggestions)
        platform_fit = ContentScorer._score_platform_fit(text, platform, issues, suggestions)
        hook_strength = ContentScorer._score_hook(text, issues, suggestions)
        cta_presence = ContentScorer._score_cta(text, platform, issues, suggestions)

        overall = (
            readability * 0.20
            + sentiment * 0.10
            + engagement * 0.25
            + platform_fit * 0.20
            + hook_strength * 0.15
            + cta_presence * 0.10
        )

        grade = ContentScorer._get_grade(overall)

        return ScoreBreakdown(
            readability=round(readability, 1),
            sentiment=round(sentiment, 1),
            engagement=round(engagement, 1),
            platform_fit=round(platform_fit, 1),
            hook_strength=round(hook_strength, 1),
            cta_presence=round(cta_presence, 1),
            overall=round(overall, 1),
            grade=grade,
            issues=issues,
            suggestions=suggestions,
        )

    # ── Readability ──

    @staticmethod
    def _score_readability(text: str, platform: str, issues: list, suggestions: list) -> float:
        if textstat:
            fre = textstat.flesch_reading_ease(text)
            grade_level = textstat.flesch_kincaid_grade(text)
        else:
            fre = ContentScorer._basic_readability(text)
            grade_level = ContentScorer._estimate_grade(text)

        target_fre = {
            "linkedin": 60, "twitter": 70, "instagram": 75,
            "facebook": 70, "email": 65, "ad": 80,
        }.get(platform, 65)

        diff = abs(fre - target_fre)
        score = max(0, 100 - diff * 1.5)

        if fre < 40:
            issues.append("Content is too complex — consider simpler words")
            suggestions.append("Use shorter sentences and common words")
        elif fre > 90:
            issues.append("Content may be too simple for the audience")
            suggestions.append("Add more substantive detail or data")

        if grade_level > 12:
            issues.append(f"Reading grade level is {grade_level} — aim for 8-10")
        elif grade_level < 4:
            issues.append("Content may lack depth")

        return min(100, score)

    @staticmethod
    def _basic_readability(text: str) -> float:
        sentences = max(1, len(re.split(r'[.!?]+', text)))
        words = text.split()
        syllables = sum(ContentScorer._count_syllables(w) for w in words)
        words_count = max(1, len(words))
        asl = words_count / sentences
        asw = syllables / words_count
        return 206.835 - 1.015 * asl - 84.6 * asw

    @staticmethod
    def _count_syllables(word: str) -> int:
        word = word.lower().strip()
        if len(word) <= 3:
            return 1
        vowels = "aeiou"
        count = 0
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith("e"):
            count -= 1
        return max(1, count)

    @staticmethod
    def _estimate_grade(text: str) -> float:
        words = text.split()
        sentences = max(1, len(re.split(r'[.!?]+', text)))
        return 0.39 * (len(words) / sentences) + 11.8 * (
            sum(ContentScorer._count_syllables(w) for w in words) / max(1, len(words))
        ) - 15.59

    # ── Sentiment ──

    @staticmethod
    def _score_sentiment(text: str) -> float:
        if _vader:
            scores = _vader.polarity_scores(text)
            compound = scores["compound"]
            return (compound + 1) / 2 * 100
        return ContentScorer._basic_sentiment(text)

    @staticmethod
    def _basic_sentiment(text: str) -> float:
        words = set(text.lower().split())
        pos = len(words & POSITIVE_WORDS)
        neg = len(words & NEGATIVE_WORDS)
        total = max(1, pos + neg)
        return (pos / total) * 100

    # ── Engagement ──

    @staticmethod
    def _score_engagement(text: str, issues: list, suggestions: list) -> float:
        score = 40.0
        words = text.split()
        word_count = len(words)

        if word_count < 10:
            issues.append("Content is too short to engage readers")
            suggestions.append("Aim for at least 50 words for most platforms")
            score -= 15
        elif 50 <= word_count <= 300:
            score += 10

        for pattern, weight in POWER_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            score += len(matches) * weight * 2

        if text.isupper():
            issues.append("ALL CAPS reduces readability and feels aggressive")
            suggestions.append("Use normal capitalization with strategic emphasis")
            score -= 10

        exclamations = text.count("!")
        if exclamations > 3:
            issues.append(f"Too many exclamation marks ({exclamations})")
            suggestions.append("Limit to 1-2 exclamation marks")
            score -= 5

        if re.search(r'(buy now|limited time|act fast|don\'t miss)', text, re.IGNORECASE):
            score += 5

        return min(100, max(0, score))

    # ── Platform Fit ──

    @staticmethod
    def _score_platform_fit(text: str, platform: str, issues: list, suggestions: list) -> float:
        spec = get_platform_spec(platform)
        char_count = len(text)
        max_chars = spec["max_chars"]

        if char_count > max_chars:
            issues.append(f"Too long for {platform} ({char_count}/{max_chars} chars)")
            suggestions.append(f"Trim to under {max_chars} characters")
            score = max(0, 100 - (char_count - max_chars) / max_chars * 200)
        elif char_count < 20:
            issues.append(f"Too short for {platform}")
            score = 20
        else:
            ratio = char_count / max_chars
            if ratio < 0.1:
                score = 60
            elif ratio < 0.5:
                score = 90
            elif ratio <= 0.8:
                score = 100
            else:
                score = 75

        hashtag_limit = spec.get("hashtag_limit", 0)
        hashtag_count = len(re.findall(r'#\w+', text))
        if hashtag_count > hashtag_limit and hashtag_limit > 0:
            issues.append(f"Too many hashtags for {platform} ({hashtag_count}/{hashtag_limit})")
            suggestions.append(f"Use {hashtag_limit} or fewer hashtags")
            score -= 10

        return min(100, max(0, score))

    # ── Hook Strength ──

    @staticmethod
    def _score_hook(text: str, issues: list, suggestions: list) -> float:
        first_line = text.split("\n")[0].strip()
        if not first_line:
            return 0

        score = 30.0

        if first_line[0].isdigit():
            score += 15
        if first_line.endswith("?"):
            score += 12
        if re.match(r'^["\']', first_line):
            score += 10
        if re.search(r'\b(shocking|surprising|nobody tells you|secret|myth)\b', first_line, re.I):
            score += 15
        if len(first_line) < 80:
            score += 10
        elif len(first_line) > 200:
            issues.append("Opening line is too long — hook should be short and punchy")
            suggestions.append("Lead with a short, attention-grabbing first line")
            score -= 10

        if any(first_line.lower().startswith(w) for w in ["i ", "we ", "our ", "hey "]):
            score += 5

        return min(100, max(0, score))

    # ── CTA Presence ──

    @staticmethod
    def _score_cta(text: str, platform: str, issues: list, suggestions: list) -> float:
        cta_patterns = [
            r'\b(sign up|subscribe|download|get started|learn more|click here)\b',
            r'\b(share|comment|save|follow|like|retweet|upvote)\b',
            r'\b(try|start|join|book|schedule|demo|free trial)\b',
            r'\b(drop a|let me know|what do you think|agree\?)\b',
            r'\b(link in bio|check out|visit)\b',
            r'\?',
        ]

        cta_count = sum(
            1 for p in cta_patterns if re.search(p, text, re.IGNORECASE)
        )

        if cta_count == 0:
            issues.append("No clear call-to-action found")
            suggestions.append(f"Add a {get_platform_spec(platform).get('cta_style', 'CTA')}")
            return 20

        score = min(100, 50 + cta_count * 15)
        return score

    # ── Grade ──

    @staticmethod
    def _get_grade(score: float) -> str:
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        return "F"
