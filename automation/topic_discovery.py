"""
TopPicksOnline.com — Topic Discovery
Scans multiple sources for trending and evergreen topics in the health/fitness/productivity niche.
"""

import json
import os
import sys
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_config():
    """Load config."""
    try:
        from automation import config
        return {
            "gemini_key": config.GEMINI_API_KEY,
            "model": config.GEMINI_MODEL,
            "categories": config.CATEGORIES,
            "topic_history": config.TOPIC_HISTORY,
            "articles_dir": config.ARTICLES_DIR,
        }
    except ImportError:
        return {
            "gemini_key": os.environ.get("GEMINI_API_KEY", ""),
            "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            "categories": [
                "At-Home Fitness",
                "Healthy Eating on a Budget",
                "Work-from-Home Productivity",
                "Grocery & Meal Hacks",
                "Motivation & Mental Health",
            ],
            "topic_history": "automation/data/topic_history.json",
            "articles_dir": "assets/data/pages/articles",
        }


def _load_topic_history(project_root: str) -> dict:
    """Load previously published topics."""
    cfg = _get_config()
    path = os.path.join(project_root, cfg["topic_history"])
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"published_topics": [], "published_slugs": []}


def _save_topic_history(project_root: str, history: dict):
    """Save topic history."""
    cfg = _get_config()
    path = os.path.join(project_root, cfg["topic_history"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def _load_existing_titles(project_root: str) -> list:
    """Load all existing article titles."""
    cfg = _get_config()
    articles_dir = os.path.join(project_root, cfg["articles_dir"])
    titles = []
    if os.path.exists(articles_dir):
        for f in os.listdir(articles_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(articles_dir, f), "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        titles.append(data.get("title", ""))
                except (json.JSONDecodeError, IOError):
                    pass
    return titles


def discover_topic_with_ai(project_root: str = ".") -> dict:
    """
    Use Gemini to discover a fresh, SEO-optimized topic.
    The AI considers existing content, current trends, and seasonal relevance.

    Returns:
        dict with keys: topic, category, keywords, reasoning
    """
    cfg = _get_config()
    existing_titles = _load_existing_titles(project_root)
    history = _load_topic_history(project_root)

    # Get current date context for seasonal relevance
    now = datetime.now()
    month_name = now.strftime("%B")
    year = now.year
    season = _get_season(now.month)

    existing_list = "\n".join(f"- {t}" for t in existing_titles) if existing_titles else "None yet"

    prompt = f"""You are an SEO content strategist for TopPicksOnline.com, a blog about health, fitness, productivity, and budget living.

TODAY'S DATE: {now.strftime('%Y-%m-%d')}
CURRENT MONTH: {month_name} {year}
SEASON: {season}

EXISTING ARTICLES (do NOT repeat these topics):
{existing_list}

CATEGORIES:
1. At-Home Fitness — home workouts, bodyweight exercises, weight loss, stretching
2. Healthy Eating on a Budget — meal planning, cheap healthy recipes, nutrition tips
3. Work-from-Home Productivity — focus techniques, desk setup, time management, apps
4. Grocery & Meal Hacks — shopping strategies, batch cooking, food storage
5. Motivation & Mental Health — habit building, stress management, mindfulness

YOUR TASK: Suggest ONE new article topic that:
1. Targets a HIGH-VOLUME search keyword people actively search for
2. Is DIFFERENT from all existing articles listed above
3. Is SEASONALLY RELEVANT for {month_name} (e.g., New Year fitness goals in January, summer body prep in spring, holiday meal planning in November)
4. Has a specific, compelling angle (not just a generic topic)
5. Would rank well on Google with proper SEO

Return ONLY valid JSON (no markdown, no code fences):
{{
  "topic": "Full article title with SEO keyword and compelling hook",
  "category": "Exact category name from the list above",
  "primary_keyword": "The main keyword this article targets",
  "secondary_keywords": ["3-5 related keywords"],
  "reasoning": "Brief explanation of why this topic is good right now",
  "search_intent": "What problem the reader is trying to solve",
  "estimated_monthly_searches": "Rough estimate like '10K-50K' or '1K-10K'"
}}"""

    try:
        from google import genai
        client = genai.Client(api_key=cfg["gemini_key"])

        response = client.models.generate_content(
            model=cfg["model"],
            contents=prompt,
            config={"temperature": 0.9, "max_output_tokens": 2048},
        )

        raw_text = response.text.strip()

        # Remove markdown code fences if present
        import re
        if raw_text.startswith("```"):
            raw_text = re.sub(r'^```(?:json)?\s*\n?', '', raw_text)
            raw_text = re.sub(r'\n?```\s*$', '', raw_text)

        topic_data = json.loads(raw_text)

        # Save to history
        history["published_topics"].append(topic_data["topic"])
        _save_topic_history(project_root, history)

        print(f"🔍 Discovered topic: {topic_data['topic']}")
        print(f"   Category: {topic_data['category']}")
        print(f"   Keyword: {topic_data['primary_keyword']}")
        print(f"   Reasoning: {topic_data['reasoning']}")

        return topic_data

    except Exception as e:
        print(f"❌ Topic discovery failed: {e}")
        # Fallback: use a pre-built topic pool
        return _fallback_topic(existing_titles, season)


def _get_season(month: int) -> str:
    """Get season name from month number."""
    if month in (12, 1, 2):
        return "Winter"
    elif month in (3, 4, 5):
        return "Spring"
    elif month in (6, 7, 8):
        return "Summer"
    else:
        return "Fall/Autumn"


def _fallback_topic(existing_titles: list, season: str) -> dict:
    """Fallback topic pool in case AI discovery fails."""
    topics = {
        "Winter": [
            {"topic": "Indoor Cardio Workouts: 10 Ways to Stay Active When It's Too Cold Outside", "category": "At-Home Fitness"},
            {"topic": "Warm and Healthy Winter Meals Under $5 Per Serving", "category": "Healthy Eating on a Budget"},
            {"topic": "New Year Fitness Goals That Actually Stick: A Realistic Guide", "category": "Motivation & Mental Health"},
            {"topic": "How to Beat Winter Blues and Stay Productive Working from Home", "category": "Work-from-Home Productivity"},
        ],
        "Spring": [
            {"topic": "Spring Cleaning Your Diet: 30-Day Reset Plan for Better Health", "category": "Healthy Eating on a Budget"},
            {"topic": "Outdoor to Indoor: Transition Your Workout for Allergy Season", "category": "At-Home Fitness"},
            {"topic": "Spring Meal Prep: Fresh, Light Recipes That Save You $100/Month", "category": "Grocery & Meal Hacks"},
        ],
        "Summer": [
            {"topic": "Stay Hydrated and Fit: Summer Home Workout Guide", "category": "At-Home Fitness"},
            {"topic": "Summer Grocery Guide: Seasonal Produce That Saves You Money", "category": "Grocery & Meal Hacks"},
            {"topic": "Beat the Heat: Productivity Tips for Working from Home in Summer", "category": "Work-from-Home Productivity"},
        ],
        "Fall/Autumn": [
            {"topic": "Fall Meal Prep Ideas: Cozy, Budget-Friendly Recipes for Busy Weeks", "category": "Healthy Eating on a Budget"},
            {"topic": "Back-to-Routine: Rebuilding Your Home Fitness Habit After Summer", "category": "Motivation & Mental Health"},
            {"topic": "Holiday Budget Planning: Save Money on Groceries Before December", "category": "Grocery & Meal Hacks"},
        ],
    }

    pool = topics.get(season, topics["Winter"])

    # Filter out already-covered topics
    existing_lower = [t.lower() for t in existing_titles]
    available = [t for t in pool if t["topic"].lower() not in existing_lower]

    if available:
        chosen = random.choice(available)
    else:
        chosen = random.choice(pool)

    chosen["primary_keyword"] = chosen["topic"].split(":")[0] if ":" in chosen["topic"] else chosen["topic"]
    chosen["secondary_keywords"] = []
    chosen["reasoning"] = f"Fallback seasonal topic for {season}"
    chosen["search_intent"] = "Seasonal health/fitness/productivity improvement"
    chosen["estimated_monthly_searches"] = "1K-10K"

    return chosen


# --- CLI ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Discover trending topics")
    parser.add_argument("--root", "-r", default=".", help="Project root")
    args = parser.parse_args()

    topic = discover_topic_with_ai(args.root)
    print(f"\n📋 Topic: {json.dumps(topic, indent=2)}")
