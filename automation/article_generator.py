"""
TopPicksOnline.com — Article Generator
Multi-step AI article generation using Gemini API.
Produces high-quality, SEO-optimized articles matching the exact JSON schema.
"""

import json
import os
import re
import sys
import random
from datetime import datetime

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from automation.quality_checker import validate_article, check_duplicate_topic


def _get_config():
    """Load config - supports both local file and environment variables."""
    try:
        from automation import config
        return {
            "gemini_key": config.GEMINI_API_KEY,
            "model": config.GEMINI_MODEL,
            "fallback_model": config.GEMINI_FALLBACK_MODEL,
            "temperature": config.GENERATION_TEMPERATURE,
            "max_retries": config.MAX_RETRIES,
            "categories": config.CATEGORIES,
            "articles_dir": config.ARTICLES_DIR,
        }
    except ImportError:
        # Fallback to environment variables (for GitHub Actions)
        return {
            "gemini_key": os.environ.get("GEMINI_API_KEY", ""),
            "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            "fallback_model": "gemini-2.0-flash",
            "temperature": 0.7,
            "max_retries": 3,
            "categories": [
                "At-Home Fitness",
                "Healthy Eating on a Budget",
                "Work-from-Home Productivity",
                "Grocery & Meal Hacks",
                "Motivation & Mental Health",
            ],
            "articles_dir": "assets/data/pages/articles",
        }


def _load_personas():
    """Load author personas for variety."""
    personas_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "author_personas.json"
    )
    try:
        with open(personas_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return [{"name": "TopPicksOnline Team", "tone": "helpful, practical"}]


def _load_existing_articles(project_root: str) -> tuple:
    """Load existing article slugs and titles to avoid duplicates."""
    config = _get_config()
    articles_dir = os.path.join(project_root, config["articles_dir"])
    slugs = []
    titles = []

    if os.path.exists(articles_dir):
        for filename in os.listdir(articles_dir):
            if filename.endswith(".json"):
                slugs.append(filename.replace(".json", ""))
                try:
                    with open(os.path.join(articles_dir, filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        titles.append(data.get("title", ""))
                except (json.JSONDecodeError, IOError):
                    pass

    return slugs, titles


def _build_article_prompt(topic: str, category: str, author: dict) -> str:
    """Build the comprehensive article generation prompt."""

    return f"""You are an expert content writer for TopPicksOnline.com, a health, fitness, productivity, and budget-living blog.

TASK: Write a complete, high-quality article about: "{topic}"
CATEGORY: {category}
AUTHOR: {author['name']}
AUTHOR TONE: {author.get('tone', 'helpful and practical')}

CRITICAL REQUIREMENTS:
1. Write in FIRST PERSON as {author['name']}. Include personal anecdotes with SPECIFIC numbers (e.g., "I lost 28 pounds in 12 weeks", "I cut my bill by 47%", "After testing for 6 months").
2. Every claim must feel data-backed. Include specific statistics, percentages, dollar amounts, and timeframes.
3. Content must be genuinely HELPFUL — actionable advice readers can implement TODAY.
4. Minimum 3,000 words of actual content across all fields.
5. NEVER use generic filler. Every paragraph must add value.

OUTPUT FORMAT: Return ONLY valid JSON matching this exact schema (no markdown, no code fences, just raw JSON):

{{
  "title": "Compelling title with keyword and hook (50-80 chars ideal)",
  "author": "{author['name']}",
  "date": "{datetime.now().strftime('%Y-%m-%d')}",
  "category": "{category}",
  "difficulty": "Beginner|Intermediate|Advanced",
  "readTime": "X min",
  "tags": ["6-10 SEO-optimized tags as lowercase strings"],
  "description": "Compelling meta description (150-200 chars) with personal hook and specific numbers",
  "introduction": {{
    "hook": "Opening line that grabs attention — state the problem viscerally (2-3 sentences)",
    "personalStory": "Your personal experience with this topic — include specific numbers, timeline, and emotional details (3-5 sentences)",
    "credibility": "Why readers should trust you — what results did you achieve? (2-3 sentences)",
    "promise": "What readers will learn and gain from this article (2-3 sentences)"
  }},
  "sections": [
    {{
      "theme": "Emoji + Section Theme Title",
      "emoji": "Single relevant emoji",
      "description": "What this section covers (1-2 sentences)",
      "tips": [
        {{
          "tipTitle": "Specific, actionable tip title with benefit (saves X%, takes Y minutes)",
          "tipNumber": 1,
          "description": "Brief overview of the tip (1-2 sentences)",
          "personalExperience": "Your personal experience with this specific tip — be specific and authentic (3-5 sentences)",
          "steps": ["Step-by-step instructions to implement this tip — 4-6 concrete steps"],
          "whyItWorks": ["Scientific or logical reasons why this works — 3-4 points"],
          "stats": {{
            "finding": "Key statistic or result",
            "insight": "What this means for the reader",
            "additionalContext": "Extra context or supporting data"
          }}
        }}
      ]
    }}
  ],
  "visualAids": [
    {{
      "type": "comparison_table",
      "title": "Before vs After comparison title",
      "subtitle": "Descriptive subtitle",
      "columns": ["Aspect", "Before (❌)", "After (✅)"],
      "rows": [
        ["Row label", "Before description", "After description"]
      ]
    }},
    {{
      "type": "checklist",
      "title": "Action checklist title",
      "subtitle": "Descriptive subtitle",
      "items": [
        {{
          "question": "Actionable checklist question?",
          "yesResult": "✅ Positive outcome",
          "noResult": "❌ Missed opportunity"
        }}
      ]
    }}
  ],
  "actionableBoxes": [
    {{
      "problemTitle": "Common problem readers face",
      "solutionTitle": "Your specific solution name",
      "actions": ["4-5 concrete action steps to solve this problem"],
      "successMetric": "How to measure success (specific number or outcome)"
    }}
  ],
  "expertData": [
    {{
      "statistic": "Relevant expert statistic with specific numbers",
      "source": "Credible source name (e.g., 'Harvard Health', 'Mayo Clinic', 'USDA')",
      "insight": "What this statistic means practically for the reader"
    }}
  ],
  "realStories": [
    {{
      "scenario": "Relatable scenario title",
      "story": "Brief story about this situation with specific details (2-3 sentences)",
      "lesson": "Key takeaway or lesson learned"
    }}
  ],
  "personalVoice": {{
    "biggestRealization": "The most important thing you learned about this topic (2-3 sentences)",
    "mindsetShift": "How your thinking changed — what you used to believe vs. now (2-3 sentences)",
    "encouragement": "Motivational message for readers who are just starting (2-3 sentences)",
    "honestTruth": "A candid, honest insight most articles won't tell you (2-3 sentences)"
  }},
  "conclusion": {{
    "mainMessage": "Summary of key takeaways with your personal results (3-5 sentences)",
    "keyInsight": "The single most important insight from this article (2-3 sentences)",
    "actionPlan": "Simple 3-step action plan readers can start TODAY (2-3 sentences)",
    "callToAction": "Engaging question or challenge to the reader (1-2 sentences)"
  }},
  "sources": [
    {{
      "citation": "Source name or study title",
      "type": "research|government_research|empirical_data|expert_opinion",
      "description": "What this source covers",
      "credibility": "Why this source is trustworthy"
    }}
  ]
}}

CONTENT GUIDELINES:
- Include 4-6 sections with 2-4 tips each
- Include 2-3 visualAids (at least one comparison_table and one checklist)
- Include 2-3 actionableBoxes
- Include 3-4 expertData entries with real, credible sources
- Include 2-3 realStories
- All statistics should be realistic and from plausible sources
- Write as if talking to a friend — warm, honest, slightly informal
- Include both successes AND failures in personal stories
- Every tip must have concrete steps, not vague advice

Remember: Return ONLY the JSON object. No markdown formatting, no explanations, no code fences."""


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def generate_article(topic: str, category: str = None, project_root: str = ".") -> dict:
    """
    Generate a complete article about the given topic.

    Args:
        topic: The article topic/title idea
        category: Category name (auto-selected if None)
        project_root: Path to the project root directory

    Returns:
        dict with keys: success, article_data, slug, file_path, validation
    """
    cfg = _get_config()
    personas = _load_personas()
    existing_slugs, existing_titles = _load_existing_articles(project_root)

    # Auto-select category if not provided
    if not category:
        category = _auto_select_category(topic, cfg["categories"])

    # Pick a random author matching the category
    author = _pick_author(category, personas)

    print(f"📝 Generating article: '{topic}'")
    print(f"   Category: {category}")
    print(f"   Author: {author['name']}")

    # Initialize Gemini client
    client = genai.Client(api_key=cfg["gemini_key"])

    # Try generation with retries
    for attempt in range(1, cfg["max_retries"] + 1):
        print(f"\n   Attempt {attempt}/{cfg['max_retries']}...")

        try:
            # Generate article
            prompt = _build_article_prompt(topic, category, author)

            model = cfg["model"] if attempt <= 2 else cfg["fallback_model"]
            print(f"   Using model: {model}")

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "temperature": cfg["temperature"],
                    "max_output_tokens": 65536,
                },
            )

            # Parse JSON from response
            raw_text = response.text.strip()

            # Remove markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = re.sub(r'^```(?:json)?\s*\n?', '', raw_text)
                raw_text = re.sub(r'\n?```\s*$', '', raw_text)

            article_data = json.loads(raw_text)

            # Validate quality
            validation = validate_article(article_data)

            if validation["valid"]:
                # Check for duplicate topic
                if check_duplicate_topic(article_data["title"], existing_slugs, existing_titles):
                    print(f"   ⚠️ Duplicate topic detected, retrying with different angle...")
                    topic = f"{topic} (unique angle: {random.choice(['beginner guide', 'advanced tips', 'common mistakes', 'budget-friendly', 'quick results'])})"
                    continue

                slug = _slugify(article_data["title"])
                file_path = os.path.join(project_root, cfg["articles_dir"], f"{slug}.json")

                # Save article
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(article_data, f, indent=2, ensure_ascii=False)

                print(f"   ✅ Article generated successfully!")
                print(f"   📊 Words: {validation['word_count']}")
                print(f"   📂 Saved: {file_path}")

                if validation["warnings"]:
                    for w in validation["warnings"]:
                        print(f"   ⚠️ Warning: {w}")

                return {
                    "success": True,
                    "article_data": article_data,
                    "slug": slug,
                    "file_path": file_path,
                    "validation": validation,
                }
            else:
                print(f"   ❌ Quality check failed:")
                for err in validation["errors"]:
                    print(f"      - {err}")
                if attempt < cfg["max_retries"]:
                    print(f"   🔄 Retrying...")

        except json.JSONDecodeError as e:
            print(f"   ❌ JSON parsing error: {e}")
            if attempt < cfg["max_retries"]:
                print(f"   🔄 Retrying...")

        except Exception as e:
            print(f"   ❌ Generation error: {e}")
            if attempt < cfg["max_retries"]:
                print(f"   🔄 Retrying...")

    return {
        "success": False,
        "article_data": None,
        "slug": None,
        "file_path": None,
        "validation": {"valid": False, "errors": ["All retry attempts failed"]},
    }


def _auto_select_category(topic: str, categories: list) -> str:
    """Auto-select the best category based on topic keywords."""
    topic_lower = topic.lower()

    keyword_map = {
        "At-Home Fitness": [
            "workout", "exercise", "fitness", "muscle", "strength", "cardio",
            "weight loss", "lose weight", "belly fat", "HIIT", "yoga", "stretching",
            "bodyweight", "gym", "training", "running", "abs", "push-up",
        ],
        "Healthy Eating on a Budget": [
            "meal", "diet", "nutrition", "food", "eating", "protein", "calorie",
            "recipe", "cook", "snack", "vegetable", "fruit", "vitamin",
            "supplement", "healthy eating", "balanced diet",
        ],
        "Work-from-Home Productivity": [
            "productivity", "focus", "work from home", "remote", "desk", "office",
            "time management", "schedule", "habit", "routine", "morning",
            "procrastination", "deep work", "concentration",
        ],
        "Grocery & Meal Hacks": [
            "grocery", "shopping", "budget", "save money", "cheap", "affordable",
            "meal prep", "batch cook", "freezer", "pantry", "coupon",
            "store brand", "bulk buy",
        ],
        "Motivation & Mental Health": [
            "motivation", "mental health", "stress", "anxiety", "mindset",
            "confidence", "discipline", "burnout", "self-care", "meditation",
            "sleep", "wellness", "mindful",
        ],
    }

    scores = {}
    for cat, keywords in keyword_map.items():
        score = sum(1 for kw in keywords if kw in topic_lower)
        scores[cat] = score

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] == 0:
        # Default to a random category if no keywords match
        return random.choice(categories)

    return best_cat


def _pick_author(category: str, personas: list) -> dict:
    """Pick an author whose expertise matches the category."""
    category_lower = category.lower()

    # Try to find a matching author
    matching = []
    for persona in personas:
        expertise = " ".join(persona.get("expertise", [])).lower()
        if any(word in expertise for word in category_lower.split()):
            matching.append(persona)

    if matching:
        return random.choice(matching)

    # Fallback: random author
    return random.choice(personas)


# --- CLI interface ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate an article for TopPicksOnline.com")
    parser.add_argument("topic", help="Article topic or title idea")
    parser.add_argument("--category", "-c", help="Category name (auto-detected if not provided)")
    parser.add_argument("--root", "-r", default=".", help="Project root directory")

    args = parser.parse_args()

    result = generate_article(
        topic=args.topic,
        category=args.category,
        project_root=args.root,
    )

    if result["success"]:
        print(f"\n🎉 Article published: {result['slug']}")
    else:
        print(f"\n💀 Failed to generate article")
        sys.exit(1)
