"""
TopPicksOnline.com — Quality Checker
Validates generated articles against quality standards before publishing.
"""

import json
import re


def validate_article(article_data: dict) -> dict:
    """
    Validates an article JSON against quality standards.
    Returns {"valid": True/False, "errors": [...], "warnings": [...]}
    """
    errors = []
    warnings = []

    # --- Required top-level fields ---
    required_fields = [
        "title", "author", "date", "category", "difficulty",
        "readTime", "tags", "description", "introduction",
        "sections", "conclusion"
    ]
    for field in required_fields:
        if field not in article_data:
            errors.append(f"Missing required field: {field}")

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    # --- Title checks ---
    title = article_data.get("title", "")
    if len(title) < 30:
        errors.append(f"Title too short ({len(title)} chars, min 30)")
    if len(title) > 200:
        warnings.append(f"Title very long ({len(title)} chars)")

    # --- Description checks ---
    desc = article_data.get("description", "")
    if len(desc) < 80:
        errors.append(f"Description too short ({len(desc)} chars, min 80)")
    if len(desc) > 500:
        warnings.append(f"Description very long ({len(desc)} chars)")

    # --- Tags checks ---
    tags = article_data.get("tags", [])
    if len(tags) < 4:
        errors.append(f"Too few tags ({len(tags)}, min 4)")
    if len(tags) > 15:
        warnings.append(f"Many tags ({len(tags)})")

    # --- Category check ---
    valid_categories = [
        "At-Home Fitness",
        "Healthy Eating on a Budget",
        "Work-from-Home Productivity",
        "Grocery & Meal Hacks",
        "Motivation & Mental Health",
    ]
    if article_data.get("category") not in valid_categories:
        warnings.append(f"Unknown category: {article_data.get('category')}")

    # --- Introduction checks ---
    intro = article_data.get("introduction", {})
    intro_fields = ["hook", "personalStory", "credibility", "promise"]
    for field in intro_fields:
        if field not in intro or not intro[field]:
            errors.append(f"Introduction missing field: {field}")

    # --- Sections checks ---
    sections = article_data.get("sections", [])
    if len(sections) < 3:
        errors.append(f"Too few sections ({len(sections)}, min 3)")

    # Count total content words
    total_words = _count_words(article_data)
    if total_words < 2000:
        errors.append(f"Article too short ({total_words} words, min 2000)")
    if total_words < 2500:
        warnings.append(f"Article is short ({total_words} words, target 2500+)")

    # --- Conclusion checks ---
    conclusion = article_data.get("conclusion", {})
    if not conclusion.get("mainMessage"):
        errors.append("Conclusion missing mainMessage")
    if not conclusion.get("callToAction"):
        warnings.append("Conclusion missing callToAction")

    # --- Optional but valuable fields ---
    optional_fields = [
        "visualAids", "actionableBoxes", "expertData",
        "realStories", "personalVoice", "sources"
    ]
    present_optional = sum(1 for f in optional_fields if f in article_data and article_data[f])
    if present_optional < 3:
        warnings.append(f"Only {present_optional}/6 optional enrichment fields present (target 3+)")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "word_count": total_words,
        "sections_count": len(sections),
        "tags_count": len(tags),
        "optional_fields": present_optional,
    }


def _count_words(obj) -> int:
    """Recursively count all words in a JSON structure."""
    if isinstance(obj, str):
        return len(obj.split())
    elif isinstance(obj, list):
        return sum(_count_words(item) for item in obj)
    elif isinstance(obj, dict):
        return sum(_count_words(value) for value in obj.values())
    return 0


def check_duplicate_topic(title: str, existing_slugs: list, existing_titles: list) -> bool:
    """Check if a topic has already been covered."""
    slug = _slugify(title)
    if slug in existing_slugs:
        return True

    # Check title similarity (simple word overlap)
    title_words = set(title.lower().split())
    for existing in existing_titles:
        existing_words = set(existing.lower().split())
        overlap = len(title_words & existing_words)
        similarity = overlap / max(len(title_words), len(existing_words))
        if similarity > 0.7:
            return True

    return False


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')
