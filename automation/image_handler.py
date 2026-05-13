"""
TopPicksOnline.com — Image Handler
Fetches high-quality, relevant stock photos from Unsplash and Pexels.
Smart keyword extraction ensures images match article content.
"""

import json
import os
import re
import sys
import requests
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_config():
    """Load config."""
    try:
        from automation import config
        return {
            "unsplash_key": config.UNSPLASH_ACCESS_KEY,
            "image_width": config.IMAGE_WIDTH,
            "image_height": config.IMAGE_HEIGHT,
            "images_dir": config.IMAGES_DIR,
        }
    except ImportError:
        return {
            "unsplash_key": os.environ.get("UNSPLASH_ACCESS_KEY", ""),
            "image_width": 1200,
            "image_height": 630,
            "images_dir": "assets/images",
        }


def _extract_keywords(article_data: dict) -> list:
    """
    Extract smart search keywords from article data.
    Returns a list of search queries, best first.
    """
    queries = []

    category = article_data.get("category", "")
    tags = article_data.get("tags", [])
    title = article_data.get("title", "")

    # Strategy 1: Category + primary tag (most relevant)
    if tags:
        queries.append(f"{category} {tags[0]}")

    # Strategy 2: Top 2-3 tags combined
    if len(tags) >= 2:
        queries.append(f"{tags[0]} {tags[1]}")
    if len(tags) >= 3:
        queries.append(f"{tags[0]} {tags[1]} {tags[2]}")

    # Strategy 3: Category-specific visual keywords
    category_visuals = {
        "At-Home Fitness": ["home workout exercise", "fitness training person", "yoga mat exercise"],
        "Healthy Eating on a Budget": ["healthy food meal", "fresh vegetables cooking", "meal prep containers"],
        "Work-from-Home Productivity": ["home office desk", "productive workspace laptop", "remote work setup"],
        "Grocery & Meal Hacks": ["grocery shopping cart", "supermarket produce", "kitchen cooking food"],
        "Motivation & Mental Health": ["meditation wellness", "peaceful morning routine", "mindfulness nature"],
    }
    if category in category_visuals:
        queries.extend(category_visuals[category])

    # Strategy 4: Key title words (fallback)
    stop_words = {"the", "a", "an", "to", "for", "and", "or", "but", "in", "on",
                  "at", "of", "by", "your", "you", "how", "what", "why", "that",
                  "this", "with", "from", "can", "will", "its", "i", "my"}
    title_words = [w for w in title.lower().split() if w not in stop_words and len(w) > 3]
    if title_words:
        queries.append(" ".join(title_words[:3]))

    return queries


def _search_unsplash(query: str, api_key: str) -> dict | None:
    """Search Unsplash for a photo matching the query."""
    try:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "per_page": 5,
            "orientation": "landscape",
            "content_filter": "high",
        }
        headers = {"Authorization": f"Client-ID {api_key}"}

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                # Pick the best result (first is most relevant)
                photo = results[0]
                return {
                    "url": photo["urls"]["regular"],
                    "download_url": photo["links"]["download_location"],
                    "photographer": photo["user"]["name"],
                    "photographer_url": photo["user"]["links"]["html"],
                    "alt_description": photo.get("alt_description", ""),
                    "source": "unsplash",
                    "query_used": query,
                }
        elif response.status_code == 403:
            print(f"   ⚠️ Unsplash rate limit reached")
        else:
            print(f"   ⚠️ Unsplash returned {response.status_code}")

    except Exception as e:
        print(f"   ⚠️ Unsplash search failed: {e}")

    return None


def _search_pexels(query: str) -> dict | None:
    """Search Pexels for a photo (no API key needed for basic search)."""
    try:
        # Pexels free API endpoint
        url = f"https://api.pexels.com/v1/search"
        params = {
            "query": query,
            "per_page": 5,
            "orientation": "landscape",
        }
        # Pexels requires an API key too, but we'll use Unsplash as primary
        # This is a fallback placeholder - user can add Pexels key later
        return None

    except Exception as e:
        print(f"   ⚠️ Pexels search failed: {e}")
        return None


def _download_image(url: str, save_path: str, width: int = 1200) -> bool:
    """Download an image from URL and save it locally."""
    try:
        # For Unsplash, we can specify dimensions in URL
        if "unsplash.com" in url:
            url = f"{url}&w={width}&q=80"

        response = requests.get(url, timeout=30, stream=True)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"   ❌ Download failed with status {response.status_code}")

    except Exception as e:
        print(f"   ❌ Download error: {e}")

    return False


def _trigger_unsplash_download(download_url: str, api_key: str):
    """Trigger Unsplash download endpoint (required by their guidelines)."""
    try:
        headers = {"Authorization": f"Client-ID {api_key}"}
        requests.get(download_url, headers=headers, timeout=10)
    except Exception:
        pass  # Non-critical


def _get_used_images(project_root: str) -> set:
    """Get set of image filenames already used to avoid duplicates."""
    cfg = _get_config()
    images_dir = os.path.join(project_root, cfg["images_dir"])
    if os.path.exists(images_dir):
        return set(os.listdir(images_dir))
    return set()


def fetch_cover_image(article_data: dict, slug: str, project_root: str = ".") -> dict:
    """
    Fetch a relevant cover image for the article.

    Args:
        article_data: The article JSON data
        slug: Article slug for filename
        project_root: Project root directory

    Returns:
        dict with keys: success, image_path, source, photographer
    """
    cfg = _get_config()
    keywords = _extract_keywords(article_data)

    save_path = os.path.join(project_root, cfg["images_dir"], f"{slug}.jpg")

    # Skip if image already exists
    if os.path.exists(save_path):
        print(f"   📸 Image already exists: {save_path}")
        return {"success": True, "image_path": save_path, "source": "existing", "photographer": ""}

    print(f"   📸 Searching for cover image...")

    # Try each keyword query
    for query in keywords:
        print(f"      Trying: '{query}'")
        photo = _search_unsplash(query, cfg["unsplash_key"])

        if photo:
            print(f"      ✅ Found: '{photo['alt_description'] or query}' by {photo['photographer']}")

            if _download_image(photo["url"], save_path, cfg["image_width"]):
                # Trigger download tracking (Unsplash requirement)
                _trigger_unsplash_download(photo["download_url"], cfg["unsplash_key"])

                print(f"      💾 Saved: {save_path}")
                return {
                    "success": True,
                    "image_path": save_path,
                    "source": photo["source"],
                    "photographer": photo["photographer"],
                    "photographer_url": photo["photographer_url"],
                }

    # All queries failed
    print(f"   ❌ Could not find a suitable cover image")
    return {
        "success": False,
        "image_path": None,
        "source": None,
        "photographer": None,
    }


# --- CLI interface ---
if __name__ == "__main__":
    # Test with a sample article
    test_article = {
        "title": "How to Lose Belly Fat at Home",
        "category": "At-Home Fitness",
        "tags": ["belly fat", "home workout", "weight loss"],
    }
    result = fetch_cover_image(test_article, "test-belly-fat-article")
    print(f"\nResult: {json.dumps(result, indent=2)}")
