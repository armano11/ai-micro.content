"""
Content Store — SQLite storage for multiplex results.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from config import settings


DB_PATH = settings.data_dir / "content_library.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS multiplex_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id TEXT UNIQUE NOT NULL,
            original_text TEXT NOT NULL,
            topic TEXT DEFAULT '',
            variant_count INTEGER DEFAULT 0,
            avg_score REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS content_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            content TEXT NOT NULL,
            hashtags TEXT DEFAULT '[]',
            score_overall REAL DEFAULT 0.0,
            score_readability REAL DEFAULT 0.0,
            score_sentiment REAL DEFAULT 0.0,
            score_engagement REAL DEFAULT 0.0,
            score_platform_fit REAL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (result_id) REFERENCES multiplex_results(result_id)
        );

        CREATE TABLE IF NOT EXISTS topic_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            platform TEXT NOT NULL,
            avg_score REAL DEFAULT 0.0,
            count INTEGER DEFAULT 1,
            last_used TEXT NOT NULL,
            UNIQUE(topic, platform)
        );

        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            rating INTEGER NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (result_id) REFERENCES multiplex_results(result_id)
        );
    """)
    conn.commit()
    conn.close()


def save_result(result_dict: dict):
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO multiplex_results
               (result_id, original_text, topic, variant_count, avg_score, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                result_dict["result_id"],
                result_dict["original_text"],
                result_dict.get("topic", ""),
                len(result_dict.get("variants", [])),
                _calc_avg_score(result_dict),
                result_dict.get("created_at", datetime.now().isoformat()),
            ),
        )

        for v in result_dict.get("variants", []):
            score = v.get("score") or {}
            conn.execute(
                """INSERT INTO content_variants
                   (result_id, platform, content, hashtags, score_overall,
                    score_readability, score_sentiment, score_engagement,
                    score_platform_fit, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result_dict["result_id"],
                    v["platform"],
                    v["content"],
                    json.dumps(v.get("hashtags", [])),
                    score.get("overall", 0),
                    score.get("readability", 0),
                    score.get("sentiment", 0),
                    score.get("engagement", 0),
                    score.get("platform_fit", 0),
                    datetime.now().isoformat(),
                ),
            )

            topic = result_dict.get("topic", "")
            if topic:
                conn.execute(
                    """INSERT INTO topic_history (topic, platform, avg_score, count, last_used)
                       VALUES (?, ?, ?, 1, ?)
                       ON CONFLICT(topic, platform) DO UPDATE SET
                       avg_score = (avg_score + ?) / 2,
                       count = count + 1,
                       last_used = ?""",
                    (topic, v["platform"], score.get("overall", 0),
                     datetime.now().isoformat(),
                     score.get("overall", 0),
                     datetime.now().isoformat()),
                )

        conn.commit()
    finally:
        conn.close()


def _calc_avg_score(result: dict) -> float:
    variants = result.get("variants", [])
    if not variants:
        return 0
    scores = [v.get("score", {}).get("overall", 0) for v in variants if v.get("score")]
    return sum(scores) / len(scores) if scores else 0


def get_recent_results(limit: int = 20) -> list:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM multiplex_results ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_result_with_variants(result_id: str) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM multiplex_results WHERE result_id = ?",
            (result_id,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        variants = conn.execute(
            "SELECT * FROM content_variants WHERE result_id = ?",
            (result_id,),
        ).fetchall()
        result["variants"] = [dict(v) for v in variants]
        return result
    finally:
        conn.close()


def get_topic_stats() -> list:
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT topic, platform, avg_score, count, last_used
               FROM topic_history ORDER BY count DESC LIMIT 50"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_total_results() -> int:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) as total FROM multiplex_results").fetchone()
        return row["total"] if row else 0
    finally:
        conn.close()


def get_total_variants() -> int:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) as total FROM content_variants").fetchone()
        return row["total"] if row else 0
    finally:
        conn.close()


def delete_result(result_id: str):
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM content_variants WHERE result_id = ?", (result_id,))
        conn.execute("DELETE FROM multiplex_results WHERE result_id = ?", (result_id,))
        conn.commit()
    finally:
        conn.close()


# ── Feedback ──


def save_feedback(result_id: str, platform: str, rating: int, note: str = ""):
    """rating: 1 = thumbs up, -1 = thumbs down"""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO user_feedback (result_id, platform, rating, note, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (result_id, platform, rating, note, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_user_preferences() -> dict:
    """Returns which platforms and score ranges the user tends to like."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT cv.platform, cv.score_overall, uf.rating
           FROM user_feedback uf
           JOIN content_variants cv ON uf.result_id = cv.result_id AND uf.platform = cv.platform
           ORDER BY uf.created_at DESC"""
    ).fetchall()
    conn.close()

    if not rows:
        return {"avg_liked_score": 0, "preferred_platforms": {}, "total_ratings": 0}

    platform_ratings = {}
    liked_scores = []
    for r in rows:
        p = r["platform"]
        if p not in platform_ratings:
            platform_ratings[p] = {"likes": 0, "dislikes": 0}
        if r["rating"] > 0:
            platform_ratings[p]["likes"] += 1
            liked_scores.append(r["score_overall"])
        else:
            platform_ratings[p]["dislikes"] += 1

    return {
        "avg_liked_score": round(sum(liked_scores) / len(liked_scores), 1) if liked_scores else 0,
        "preferred_platforms": platform_ratings,
        "total_ratings": len(rows),
    }


def get_feedback_history(limit: int = 50) -> list:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT uf.*, cv.content, cv.score_overall
           FROM user_feedback uf
           LEFT JOIN content_variants cv ON uf.result_id = cv.result_id AND uf.platform = cv.platform
           ORDER BY uf.created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


init_db()
