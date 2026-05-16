"""
Pinterest Auto-Pin Script for TopPicksOnline
=============================================
Automatically creates Pinterest pins for all articles.
Uses the Pinterest API v5 to post pins with images.

Setup:
  1. Create a Pinterest app at developers.pinterest.com
  2. Generate an access token with pins:write and boards:read scopes
  3. Set your token below or as environment variable PINTEREST_TOKEN
  4. Run: python pinterest_autoposter.py

Usage:
  python pinterest_autoposter.py                  # Post pins for ALL articles
  python pinterest_autoposter.py --article slug   # Post pin for ONE article
  python pinterest_autoposter.py --dry-run        # Preview without posting
"""

import json
import os
import sys
import time
import re
import urllib.request
import urllib.error
import urllib.parse

# ============================================
# CONFIGURATION — Edit these values
# ============================================
PINTEREST_TOKEN = os.environ.get('PINTEREST_TOKEN', 'YOUR_TOKEN_HERE')
SITE_URL = 'https://topicksonline.com'

# Map article categories to Pinterest board names
# After creating boards, you can find board IDs by running: --list-boards
CATEGORY_TO_BOARD = {
    'Grocery & Meal Hacks': 'healthy-meals-on-a-budget',
    'Healthy Eating on a Budget': 'healthy-meals-on-a-budget',
    'At-Home Fitness': 'home-workouts-for-beginners',
    'Work-from-Home Productivity': 'work-from-home-tips',
    'Motivation & Mental Health': 'budget-living-tips',
}
DEFAULT_BOARD = 'budget-living-tips'

# Pinterest API base
API_BASE = 'https://api.pinterest.com/v5'

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(BASE_DIR, 'assets', 'data', 'pages', 'articles')
POSTED_LOG = os.path.join(BASE_DIR, 'automation', 'pinterest_posted.json')

# ============================================
# Pinterest API Functions
# ============================================

def pinterest_request(endpoint, method='GET', data=None):
    """Make a request to the Pinterest API."""
    url = f'{API_BASE}{endpoint}'
    headers = {
        'Authorization': f'Bearer {PINTEREST_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"  API Error {e.code}: {error_body}")
        return None


def list_boards():
    """List all Pinterest boards for the authenticated user."""
    result = pinterest_request('/boards')
    if result and 'items' in result:
        print("\nYour Pinterest Boards:")
        print("-" * 60)
        for board in result['items']:
            print(f"  Name: {board['name']}")
            print(f"  ID:   {board['id']}")
            slug = board['name'].lower().replace(' ', '-')
            slug = re.sub(r'[^a-z0-9-]', '', slug)
            print(f"  Slug: {slug}")
            print()
        return result['items']
    else:
        print("Could not fetch boards. Check your token.")
        return []


def create_pin(board_id, title, description, link, image_url):
    """Create a pin on Pinterest."""
    data = {
        'board_id': board_id,
        'title': title[:100],  # Pinterest title limit
        'description': description[:500],  # Pinterest description limit  
        'link': link,
        'media_source': {
            'source_type': 'image_url',
            'url': image_url
        }
    }
    
    return pinterest_request('/pins', method='POST', data=data)


def get_board_id_by_slug(boards, slug):
    """Find a board ID by its slug name."""
    for board in boards:
        board_slug = board['name'].lower().replace(' ', '-')
        board_slug = re.sub(r'[^a-z0-9-]', '', board_slug)
        if board_slug == slug:
            return board['id']
    return None


# ============================================
# Pin Content Generator
# ============================================

def strip_emojis(text):
    """Remove emojis from text."""
    if not text:
        return ''
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
        "\U0001f900-\U0001f9FF\U0001fa00-\U0001fa6f\U0001fa70-\U0001faff"
        "\U00002600-\U000026FF\U0000FE00-\U0000FE0F\U0000200D]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text).strip()


def generate_pin_description(article_data):
    """Generate a Pinterest-optimized description with keywords."""
    title = strip_emojis(article_data.get('title', ''))
    description = article_data.get('description', '')
    category = article_data.get('category', '')
    tags = article_data.get('tags', [])
    
    # Build a keyword-rich description
    parts = []
    
    # Main description
    if description:
        parts.append(description)
    
    # Add a call to action
    parts.append(f"Read the full guide at TopPicksOnline.com")
    
    # Add hashtag-style keywords
    if tags:
        keyword_str = ' | '.join(tags[:6])
        parts.append(keyword_str)
    
    return ' '.join(parts)


def get_article_image_url(article_data, slug):
    """Get the best image URL for the article."""
    # Try thumbnail first, then image, then construct from slug
    image = article_data.get('thumbnail', article_data.get('image', ''))
    if image and image.startswith('/'):
        return f"{SITE_URL}{image}"
    elif image and image.startswith('http'):
        return image
    else:
        return f"{SITE_URL}/assets/images/{slug}.jpg"


# ============================================
# Posted Articles Tracking
# ============================================

def load_posted_log():
    """Load the log of already-posted articles."""
    if os.path.exists(POSTED_LOG):
        with open(POSTED_LOG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_posted_log(log):
    """Save the posted articles log."""
    os.makedirs(os.path.dirname(POSTED_LOG), exist_ok=True)
    with open(POSTED_LOG, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2)


# ============================================
# Main Logic
# ============================================

def post_pins_for_article(slug, article_data, boards, dry_run=False):
    """Create Pinterest pin(s) for a single article."""
    title = strip_emojis(article_data.get('title', ''))
    category = article_data.get('category', '')
    description = generate_pin_description(article_data)
    link = f"{SITE_URL}/articles/{slug}"
    image_url = get_article_image_url(article_data, slug)
    
    # Find the right board
    board_slug = CATEGORY_TO_BOARD.get(category, DEFAULT_BOARD)
    board_id = get_board_id_by_slug(boards, board_slug)
    
    if not board_id:
        print(f"  [WARN] Board '{board_slug}' not found. Using first available board.")
        if boards:
            board_id = boards[0]['id']
        else:
            print(f"  [ERR] No boards found! Create boards first.")
            return False
    
    print(f"  Title: {title[:60]}...")
    print(f"  Board: {board_slug}")
    print(f"  Link:  {link}")
    print(f"  Image: {image_url}")
    
    if dry_run:
        print(f"  [DRY RUN] Would create pin")
        return True
    
    result = create_pin(board_id, title, description, link, image_url)
    if result and 'id' in result:
        print(f"  [OK] Pin created: {result['id']}")
        return True
    else:
        print(f"  [ERR] Failed to create pin")
        return False


def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    list_boards_only = '--list-boards' in args
    specific_article = None
    
    if '--article' in args:
        idx = args.index('--article')
        if idx + 1 < len(args):
            specific_article = args[idx + 1]
    
    # Check token
    if PINTEREST_TOKEN == 'YOUR_TOKEN_HERE':
        print("=" * 50)
        print("Pinterest API token not set!")
        print()
        print("Set it in one of these ways:")
        print("  1. Edit this file and replace YOUR_TOKEN_HERE")
        print("  2. Set environment variable: ")
        print("     set PINTEREST_TOKEN=your_token_here")
        print()
        print("Get your token at: developers.pinterest.com")
        print("=" * 50)
        return
    
    # List boards mode
    if list_boards_only:
        list_boards()
        return
    
    # Get boards
    print("Fetching Pinterest boards...")
    result = pinterest_request('/boards')
    if not result or 'items' not in result:
        print("Failed to fetch boards. Check your API token.")
        return
    
    boards = result['items']
    print(f"Found {len(boards)} boards\n")
    
    # Load posted log
    posted = load_posted_log()
    
    # Get articles
    if specific_article:
        article_files = [f"{specific_article}.json"]
    else:
        article_files = [f for f in os.listdir(ARTICLES_DIR) if f.endswith('.json')]
    
    print(f"Processing {len(article_files)} articles...\n")
    
    created = 0
    skipped = 0
    errors = 0
    
    for filename in article_files:
        slug = filename.replace('.json', '')
        filepath = os.path.join(ARTICLES_DIR, filename)
        
        # Skip already posted
        if slug in posted and not specific_article:
            skipped += 1
            continue
        
        print(f"--- {slug} ---")
        
        if not os.path.exists(filepath):
            print(f"  [ERR] File not found: {filepath}")
            errors += 1
            continue
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                article_data = json.load(f)
            
            success = post_pins_for_article(slug, article_data, boards, dry_run)
            
            if success and not dry_run:
                posted[slug] = {
                    'posted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'title': strip_emojis(article_data.get('title', ''))
                }
                save_posted_log(posted)
                created += 1
            elif success:
                created += 1
            else:
                errors += 1
            
            # Rate limiting — Pinterest allows ~10 requests/minute
            if not dry_run:
                time.sleep(6)
                
        except Exception as e:
            print(f"  [ERR] {e}")
            errors += 1
    
    print(f"\n{'=' * 50}")
    print(f"Pinterest Auto-Pin Complete!")
    print(f"  Created: {created}")
    print(f"  Skipped (already posted): {skipped}")
    print(f"  Errors: {errors}")
    if dry_run:
        print(f"  (DRY RUN - nothing was actually posted)")


if __name__ == '__main__':
    main()
