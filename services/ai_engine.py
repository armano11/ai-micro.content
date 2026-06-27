"""
AI Engine — LLM-powered content transformation.
Uses NVIDIA NIM (LLaMA) or OpenAI as fallback.
"""

import httpx
import re
import json
import asyncio
from config import settings


SYSTEM_PROMPT = """You are a world-class marketing copywriter. You transform content for different platforms while preserving the core message. You understand platform-specific norms, audience behavior, and engagement patterns.

RULES:
- Stay faithful to the original message — never add claims not in the source
- Adapt tone, length, and format for the target platform
- Use platform-appropriate language and structure
- Make every word count — no filler, no fluff
- Output ONLY the transformed content, nothing else
- No explanations, no preambles, no "Here's the LinkedIn version:" — just the content"""


PLATFORM_PROMPTS = {
    "linkedin": """
Write a LinkedIn post. Rules:
- Open with a bold, pattern-interrupt first line (statistic, hot take, or counterintuitive claim)
- Use line breaks between ideas — no walls of text
- Write in first person ("I", "We") for authenticity
- Include 1-2 data points or specific numbers if available
- End with a thought-provoking question to drive comments
- 150-1000 characters optimal
- No hashtags in the body — they go at the end if needed (max 3)
- Professional but not corporate — write like a human, not a brochure""",

    "twitter": """
Write a Twitter/X post. Rules:
- One idea per sentence, max 2-3 sentences
- Lead with the most interesting point — no throat-clearing
- Use numbers and specifics ("3 tips" not "some tips")
- Under 260 characters for engagement (leave room for retweets with comment)
- No hashtags in the main tweet — add 1-2 at the end if relevant
- Punchy, direct, no passive voice
- If the content is long, write as a thread (2-5 tweets, each under 280 chars)
- End the thread with a summary or CTA""",

    "instagram": """
Write an Instagram caption. Rules:
- First line is the hook — it shows in feed preview, make it count
- Use line breaks for scannability — short paragraphs, 1-2 sentences each
- Casual, relatable, conversational tone
- Include 1-2 relevant emojis per paragraph (not every sentence)
- End with a clear CTA: "Save this", "Share with someone who needs this", "Drop a 🔥 if you agree"
- Add 15-25 relevant hashtags at the bottom, separated by line break
- Max 2200 characters""",

    "facebook": """
Write a Facebook post. Rules:
- Open with a question or relatable scenario
- Conversational, warm, community-oriented tone
- Short paragraphs (1-2 sentences max)
- Use storytelling — make the reader feel something
- End with a discussion prompt: "What's your experience?" or "Agree?"
- No external links in the post body
- 1-3 emojis max, used naturally
- Max 1000 characters for optimal reach""",

    "email": """
Write an email newsletter body. Rules:
- Personal greeting: "Hi [Name]," or "Hey there,"
- Opening line should acknowledge a pain point or desire
- Value-first: give insight before asking for anything
- Use short paragraphs and bullet points for scannability
- ONE clear CTA — make it obvious what to do next
- Warm, personal, like writing to a friend who's a professional
- Sign off naturally — "Cheers", "Talk soon", etc.
- 200-500 words optimal""",

    "ad": """
Write ad copy. Rules:
- Lead with the outcome/benefit, not the feature
- First line: hook the pain point or desired result
- Use power words: proven, instant, free, exclusive, guaranteed
- Create urgency: "limited spots", "before midnight", "only X left"
- Social proof if available: numbers, testimonials, results
- ONE clear CTA: "Start free trial", "Download now", "Get started"
- Under 300 characters
- Every word must earn its place — cut anything that doesn't drive action""",
}


def _build_transform_prompt(text: str, platform: str, spec: dict, topic: str = "") -> str:
    topic_line = f"TOPIC/CAMPAIGN: {topic}\n" if topic else ""
    platform_prompt = PLATFORM_PROMPTS.get(platform, "")

    return f"""{SYSTEM_PROMPT}

{platform_prompt}

{topic_line}
CHARACTER LIMIT: {spec['max_chars']}

ORIGINAL CONTENT:
{text.strip()}

Write the {platform} version now. Output ONLY the content:"""


async def _call_nvidia(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.nvidia_base_url}/chat/completions",
            json={
                "model": settings.content_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1500,
            },
            headers=headers,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        raise Exception(f"NVIDIA API error: {resp.status_code} - {resp.text[:200]}")


async def _call_openai(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": settings.openai_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1500,
            },
            headers=headers,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        raise Exception(f"OpenAI API error: {resp.status_code}")


async def transform_content(text: str, platform: str, spec: dict, topic: str = "") -> str:
    """Call LLM to transform content for a specific platform."""
    prompt = _build_transform_prompt(text, platform, spec, topic)

    if settings.nvidia_configured:
        try:
            return await _call_nvidia(prompt)
        except Exception as e:
            print(f"[AI Engine] NVIDIA failed: {e}")

    if settings.openai_configured:
        try:
            return await _call_openai(prompt)
        except Exception as e:
            print(f"[AI Engine] OpenAI failed: {e}")

    return _fallback_transform(text, platform, spec)


def _fallback_transform(text: str, platform: str, spec: dict) -> str:
    """Rule-based transformation when no API key is available."""
    clean = re.sub(r'\s+', ' ', text).strip()

    if platform == "twitter":
        sentences = re.split(r'(?<=[.!?])\s+', clean)
        tweets = []
        current = ""
        for s in sentences:
            if len(current) + len(s) < 260:
                current += " " + s if current else s
            else:
                if current:
                    tweets.append(current)
                current = s
        if current:
            tweets.append(current)
        return "\n\n".join(f"{'🧵 ' if i == 0 else ''}{t.strip()}" for i, t in enumerate(tweets[:6]))

    elif platform == "instagram":
        lines = clean.split(". ")
        caption_lines = []
        for line in lines:
            caption_lines.append(line.strip().rstrip("."))
        caption = "\n\n".join(caption_lines[:8])
        hashtags = " ".join(["#marketing", "#growth", "#tips", "#business", "#contentcreator"])
        return f"✨ {caption}\n\n{hashtags}"

    elif platform == "linkedin":
        sentences = re.split(r'(?<=[.!?])\s+', clean)
        paragraphs = []
        current = ""
        for s in sentences:
            if len(current) + len(s) < 200:
                current += " " + s if current else s
            else:
                if current:
                    paragraphs.append(current)
                current = s
        if current:
            paragraphs.append(current)
        return "\n\n".join(paragraphs[:6])

    elif platform == "email":
        sentences = re.split(r'(?<=[.!?])\s+', clean)
        body = " ".join(sentences[:6])
        return f"Hi there,\n\n{body}\n\nBest regards"

    elif platform == "ad":
        sentences = re.split(r'(?<=[.!?])\s+', clean)
        return f"🎯 {sentences[0]}\n\n👉 {sentences[-1]}" if sentences else clean[:300]

    elif platform == "facebook":
        sentences = re.split(r'(?<=[.!?])\s+', clean)
        return "\n\n".join(sentences[:5])

    return clean[:spec.get("max_chars", 500)]
