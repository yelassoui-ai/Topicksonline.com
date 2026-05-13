"""
TopPicksOnline.com — Master Pipeline
One command runs the entire automation: discover topic → generate article → 
fetch image → build site → commit → deploy → post to social media.

Usage:
    python pipeline.py                    # Full auto: discover topic + generate + deploy + social
    python pipeline.py --topic "..."      # Use a specific topic
    python pipeline.py --no-social        # Skip social media posting
    python pipeline.py --dry-run          # Generate but don't commit/deploy
"""

import json
import os
import sys
import subprocess
import argparse
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from automation.topic_discovery import discover_topic_with_ai
from automation.article_generator import generate_article
from automation.image_handler import fetch_cover_image
from automation.social_poster import post_to_all_platforms


def run_pipeline(
    topic: str = None,
    category: str = None,
    skip_social: bool = False,
    dry_run: bool = False,
    project_root: str = None,
):
    """
    Run the full content automation pipeline.

    Args:
        topic: Specific topic (auto-discovered if None)
        category: Specific category (auto-detected if None)
        skip_social: Skip social media posting
        dry_run: Generate content but don't commit/deploy
        project_root: Project root directory
    """
    if project_root is None:
        project_root = PROJECT_ROOT

    start_time = datetime.now()
    print("=" * 70)
    print(f"🚀 TopPicksOnline.com — Automation Pipeline")
    print(f"   Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 70)

    results = {
        "started": start_time.isoformat(),
        "topic_discovery": None,
        "article_generation": None,
        "image_fetch": None,
        "site_build": None,
        "git_deploy": None,
        "social_media": None,
        "success": False,
    }

    # ──────────────────────────────────────────────────────
    # PHASE 1: Topic Discovery
    # ──────────────────────────────────────────────────────
    print(f"\n{'─'*70}")
    print("📊 PHASE 1: Topic Discovery")
    print(f"{'─'*70}")

    if topic:
        print(f"   Using provided topic: {topic}")
        topic_data = {
            "topic": topic,
            "category": category or "At-Home Fitness",
            "primary_keyword": topic,
            "reasoning": "User-specified topic",
        }
    else:
        topic_data = discover_topic_with_ai(project_root)

    results["topic_discovery"] = {
        "topic": topic_data["topic"],
        "category": topic_data.get("category", ""),
    }

    # ──────────────────────────────────────────────────────
    # PHASE 2: Article Generation
    # ──────────────────────────────────────────────────────
    print(f"\n{'─'*70}")
    print("✍️  PHASE 2: Article Generation")
    print(f"{'─'*70}")

    article_result = generate_article(
        topic=topic_data["topic"],
        category=topic_data.get("category"),
        project_root=project_root,
    )

    results["article_generation"] = {
        "success": article_result["success"],
        "slug": article_result.get("slug"),
        "word_count": article_result.get("validation", {}).get("word_count", 0),
    }

    if not article_result["success"]:
        print("\n💀 Pipeline failed at article generation.")
        results["success"] = False
        _save_run_log(project_root, results)
        return results

    slug = article_result["slug"]
    article_data = article_result["article_data"]

    # ──────────────────────────────────────────────────────
    # PHASE 3: Image Fetch
    # ──────────────────────────────────────────────────────
    print(f"\n{'─'*70}")
    print("📸 PHASE 3: Cover Image")
    print(f"{'─'*70}")

    image_result = fetch_cover_image(article_data, slug, project_root)
    results["image_fetch"] = {
        "success": image_result["success"],
        "source": image_result.get("source"),
        "photographer": image_result.get("photographer"),
    }

    # Update article data with image path
    if image_result["success"]:
        article_data["image"] = f"assets/images/{slug}.jpg"
        # Re-save article with image path
        article_path = os.path.join(project_root, "assets", "data", "pages", "articles", f"{slug}.json")
        with open(article_path, "w", encoding="utf-8") as f:
            json.dump(article_data, f, indent=2, ensure_ascii=False)

    # ──────────────────────────────────────────────────────
    # PHASE 4: Build Site
    # ──────────────────────────────────────────────────────
    print(f"\n{'─'*70}")
    print("🔧 PHASE 4: Build Site")
    print(f"{'─'*70}")

    build_success = _run_build(project_root)
    results["site_build"] = {"success": build_success}

    if not build_success:
        print("   ⚠️ Build had issues, but continuing...")

    # ──────────────────────────────────────────────────────
    # PHASE 5: Git Deploy
    # ──────────────────────────────────────────────────────
    if not dry_run:
        print(f"\n{'─'*70}")
        print("🚀 PHASE 5: Git Deploy")
        print(f"{'─'*70}")

        deploy_success = _git_deploy(project_root, slug, article_data.get("title", slug))
        results["git_deploy"] = {"success": deploy_success}
    else:
        print(f"\n{'─'*70}")
        print("🚀 PHASE 5: Git Deploy (SKIPPED — dry run)")
        print(f"{'─'*70}")
        results["git_deploy"] = {"success": False, "reason": "dry_run"}

    # ──────────────────────────────────────────────────────
    # PHASE 6: Social Media
    # ──────────────────────────────────────────────────────
    if not skip_social and not dry_run:
        print(f"\n{'─'*70}")
        print("📱 PHASE 6: Social Media Distribution")
        print(f"{'─'*70}")

        image_path = image_result.get("image_path") if image_result["success"] else None
        social_result = post_to_all_platforms(article_data, slug, image_path, project_root)
        results["social_media"] = social_result["results"]
    else:
        reason = "dry_run" if dry_run else "skipped by user"
        print(f"\n📱 PHASE 6: Social Media (SKIPPED — {reason})")
        results["social_media"] = {"skipped": True, "reason": reason}

    # ──────────────────────────────────────────────────────
    # SUMMARY
    # ──────────────────────────────────────────────────────
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results["success"] = article_result["success"]
    results["duration_seconds"] = duration
    results["ended"] = end_time.isoformat()

    print(f"\n{'='*70}")
    print(f"{'✅' if results['success'] else '❌'} Pipeline {'COMPLETED' if results['success'] else 'FAILED'}")
    print(f"   Duration: {duration:.1f} seconds")
    print(f"   Article: {article_data.get('title', 'N/A')}")
    print(f"   Slug: {slug}")
    print(f"   Words: {results['article_generation'].get('word_count', 0)}")
    print(f"   Image: {'✅' if image_result['success'] else '❌'}")
    print(f"   Deploy: {'✅' if results.get('git_deploy', {}).get('success') else '⏭️ skipped'}")
    print(f"{'='*70}")

    _save_run_log(project_root, results)
    return results


def _run_build(project_root: str) -> bool:
    """Run batch.py to rebuild homepage, categories, search index, and sitemap."""
    batch_path = os.path.join(project_root, "batch.py")
    sitemap_path = os.path.join(project_root, "sitemap_generator.py")

    success = True

    # Run batch.py
    if os.path.exists(batch_path):
        try:
            print("   Running batch.py --build...")
            result = subprocess.run(
                [sys.executable, batch_path, "--build"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                print("   ✅ batch.py completed")
            else:
                print(f"   ⚠️ batch.py returned code {result.returncode}")
                if result.stderr:
                    print(f"      {result.stderr[:200]}")
                success = False
        except subprocess.TimeoutExpired:
            print("   ⚠️ batch.py timed out")
            success = False
        except Exception as e:
            print(f"   ⚠️ batch.py error: {e}")
            success = False
    else:
        print(f"   ⚠️ batch.py not found at {batch_path}")
        success = False

    # Run sitemap_generator.py
    if os.path.exists(sitemap_path):
        try:
            print("   Running sitemap_generator.py...")
            result = subprocess.run(
                [sys.executable, sitemap_path],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                print("   ✅ Sitemap updated")
            else:
                print(f"   ⚠️ sitemap_generator.py returned code {result.returncode}")
        except Exception as e:
            print(f"   ⚠️ Sitemap error: {e}")

    return success


def _git_deploy(project_root: str, slug: str, title: str) -> bool:
    """Commit changes and push to GitHub (triggers Netlify deploy)."""
    try:
        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=project_root,
            capture_output=True,
            timeout=30,
        )

        # Commit
        commit_msg = f"📝 New article: {title}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            if "nothing to commit" in result.stdout:
                print("   ⚠️ Nothing to commit")
                return True
            print(f"   ❌ Git commit failed: {result.stderr[:200]}")
            return False

        print(f"   ✅ Committed: {commit_msg}")

        # Push
        result = subprocess.run(
            ["git", "push"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            print("   ✅ Pushed to GitHub → Netlify will auto-deploy")
            return True
        else:
            print(f"   ❌ Git push failed: {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print("   ❌ Git operation timed out")
        return False
    except FileNotFoundError:
        print("   ❌ Git not installed")
        return False
    except Exception as e:
        print(f"   ❌ Git error: {e}")
        return False


def _save_run_log(project_root: str, results: dict):
    """Save pipeline run log for tracking."""
    log_path = os.path.join(project_root, "automation", "data", "run_log.json")

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log = {"runs": []}

    log["runs"].append(results)

    # Keep only last 100 runs
    log["runs"] = log["runs"][-100:]

    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


# ──────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TopPicksOnline.com — Full Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py                          # Full auto run
  python pipeline.py --topic "best HIIT workouts for beginners"
  python pipeline.py --dry-run                # Test without deploying
  python pipeline.py --no-social              # Skip social media
        """,
    )
    parser.add_argument("--topic", "-t", help="Specific article topic")
    parser.add_argument("--category", "-c", help="Article category")
    parser.add_argument("--no-social", action="store_true", help="Skip social media posting")
    parser.add_argument("--dry-run", action="store_true", help="Generate only, don't deploy")
    parser.add_argument("--root", "-r", default=None, help="Project root directory")

    args = parser.parse_args()

    result = run_pipeline(
        topic=args.topic,
        category=args.category,
        skip_social=args.no_social,
        dry_run=args.dry_run,
        project_root=args.root,
    )

    sys.exit(0 if result["success"] else 1)
