"""
Pre-render Script for TopPicksOnline
=====================================
Generates static HTML pages for every article so Google can index them.
Run this before deploying to Netlify.

Usage: python prerender.py
"""

import json
import os
import re
import html

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(BASE_DIR, 'assets', 'data', 'pages', 'articles')
OUTPUT_BASE = BASE_DIR  # Output to project root
SITE_URL = 'https://topicksonline.com'

# Read the base index.html to extract <head> content
INDEX_PATH = os.path.join(BASE_DIR, 'index.html')


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


def escape(text):
    """HTML-escape text."""
    if not text:
        return ''
    return html.escape(str(text))


def render_article_html(article_data, slug):
    """Generate a full HTML page for an article."""
    
    title = strip_emojis(article_data.get('title', ''))
    description = article_data.get('description', '')
    author = article_data.get('author', 'TopPicksOnline Editorial Team')
    date = article_data.get('date', '')
    category = article_data.get('category', '')
    read_time = article_data.get('readTime', '')
    tags = article_data.get('tags', [])
    image = article_data.get('image', article_data.get('thumbnail', f'/assets/images/{slug}.jpg'))
    canonical_url = f'{SITE_URL}/articles/{slug}'
    
    # Build article body content
    body_parts = []
    
    # Introduction
    intro = article_data.get('introduction', {})
    if intro:
        if intro.get('hook'):
            body_parts.append(f'<p><strong>{escape(intro["hook"])}</strong></p>')
        if intro.get('personalStory'):
            body_parts.append(f'<p>{escape(intro["personalStory"])}</p>')
        if intro.get('credibility'):
            body_parts.append(f'<p>{escape(intro["credibility"])}</p>')
        if intro.get('promise'):
            body_parts.append(f'<p>{escape(intro["promise"])}</p>')
    
    # Sections
    sections = article_data.get('sections', [])
    for i, section in enumerate(sections):
        theme = strip_emojis(section.get('theme', section.get('title', '')))
        desc = section.get('description', '')
        body_parts.append(f'<h2 id="sec-{i}">{escape(theme)}</h2>')
        if desc:
            body_parts.append(f'<p>{escape(desc)}</p>')
        
        # Render tips/hacks/items etc.
        for content_type in ['tips', 'hacks', 'meals', 'principles', 'strategies', 
                              'habits', 'workoutTypes', 'steps', 'methods', 'exercises',
                              'recipes', 'items', 'techniques', 'benefits', 'solutions',
                              'recommendations', 'practices', 'problems', 'mistakes',
                              'challenges', 'tools', 'rules']:
            items = section.get(content_type, [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item_title = item.get('tipTitle', item.get('hackTitle', 
                                    item.get('title', item.get('name', ''))))
                        item_desc = item.get('description', item.get('explanation', ''))
                        item_exp = item.get('personalExperience', '')
                        
                        if item_title:
                            body_parts.append(f'<h3>{escape(strip_emojis(item_title))}</h3>')
                        if item_desc:
                            body_parts.append(f'<p>{escape(item_desc)}</p>')
                        if item_exp:
                            body_parts.append(f'<p>{escape(item_exp)}</p>')
                        
                        # Steps
                        steps = item.get('steps', item.get('howTo', []))
                        if isinstance(steps, list) and steps:
                            body_parts.append('<ul>')
                            for step in steps:
                                body_parts.append(f'<li>{escape(str(step))}</li>')
                            body_parts.append('</ul>')
                        
                        # Why it works
                        reasons = item.get('whyItWorks', item.get('benefits', []))
                        if isinstance(reasons, list) and reasons:
                            body_parts.append('<ul>')
                            for reason in reasons:
                                body_parts.append(f'<li>{escape(str(reason))}</li>')
                            body_parts.append('</ul>')
                    elif isinstance(item, str):
                        body_parts.append(f'<p>{escape(item)}</p>')
    
    # Key Takeaways
    takeaways = article_data.get('keyTakeaways', [])
    if takeaways:
        body_parts.append('<h2>Key Takeaways</h2><ul>')
        for t in takeaways:
            body_parts.append(f'<li>{escape(t)}</li>')
        body_parts.append('</ul>')
    
    # FAQ
    faq = article_data.get('faq', [])
    faq_schema = ''
    if faq:
        body_parts.append('<h2>Frequently Asked Questions</h2>')
        for item in faq:
            q = item.get('question', '')
            a = item.get('answer', '')
            body_parts.append(f'<h3>{escape(q)}</h3>')
            body_parts.append(f'<p>{escape(a)}</p>')
        
        # FAQ Schema
        faq_entries = []
        for item in faq:
            faq_entries.append({
                "@type": "Question",
                "name": item.get('question', ''),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item.get('answer', '')
                }
            })
        faq_schema_obj = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_entries
        }
        faq_schema = f'<script type="application/ld+json">{json.dumps(faq_schema_obj)}</script>'
    
    # Conclusion
    conclusion = article_data.get('conclusion', {})
    if conclusion:
        body_parts.append('<h2>Conclusion</h2>')
        if conclusion.get('mainMessage'):
            body_parts.append(f'<p>{escape(conclusion["mainMessage"])}</p>')
        if conclusion.get('keyInsight'):
            body_parts.append(f'<p><strong>{escape(conclusion["keyInsight"])}</strong></p>')
        if conclusion.get('actionPlan'):
            body_parts.append(f'<p>{escape(conclusion["actionPlan"])}</p>')
    
    # Sources
    sources = article_data.get('sources', [])
    if sources:
        body_parts.append('<h2>Sources & References</h2><ul>')
        for src in sources:
            citation = src.get('citation', '')
            src_desc = src.get('description', '')
            body_parts.append(f'<li><strong>{escape(citation)}</strong>: {escape(src_desc)}</li>')
        body_parts.append('</ul>')
    
    article_body = '\n'.join(body_parts)
    
    # Tags
    tags_html = ', '.join(tags) if tags else ''
    
    # Article Schema
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "author": {
            "@type": "Person",
            "name": author
        },
        "datePublished": date,
        "publisher": {
            "@type": "Organization",
            "name": "TopPicksOnline",
            "url": SITE_URL,
            "logo": {
                "@type": "ImageObject",
                "url": f"{SITE_URL}/favicon.PNG"
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": canonical_url
        },
        "image": f"{SITE_URL}{image}" if image.startswith('/') else image
    }
    
    # Breadcrumb Schema
    breadcrumb_items = [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL},
    ]
    if category:
        cat_slug = re.sub(r'[^a-z0-9]+', '-', category.lower()).strip('-')
        breadcrumb_items.append({
            "@type": "ListItem", "position": 2, 
            "name": category, "item": f"{SITE_URL}/category/{cat_slug}"
        })
        breadcrumb_items.append({
            "@type": "ListItem", "position": 3, "name": title
        })
    else:
        breadcrumb_items.append({
            "@type": "ListItem", "position": 2, "name": title
        })
    
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": breadcrumb_items
    }
    
    # Build full HTML
    page_html = f'''<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <base href="/" />
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{escape(title)} | TopPicksOnline</title>
    <link rel="icon" type="image/x-icon" href="/favicon.PNG" />
    <link rel="canonical" href="{canonical_url}" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Playfair+Display:wght@700;800&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="/assets/css.css" />
    <script src="/assets/js.js" defer></script>
    <meta name="description" content="{escape(description)}" />
    <meta name="author" content="{escape(author)}" />
    <meta name="keywords" content="{escape(tags_html)}" />
    <meta property="og:title" content="{escape(title)}" />
    <meta property="og:description" content="{escape(description)}" />
    <meta property="og:type" content="article" />
    <meta property="og:url" content="{canonical_url}" />
    <meta property="og:site_name" content="TopPicksOnline" />
    <meta property="og:image" content="{SITE_URL}{image}" />
    <meta property="twitter:card" content="summary_large_image" />
    <meta property="twitter:title" content="{escape(title)}" />
    <meta property="twitter:description" content="{escape(description)}" />
    <meta property="twitter:site" content="@TopPicksOnline" />
    <meta name="p:domain_verify" content="49bcbb34926943ef505e930bb1bb353b" />
    <meta name="impact-site-verification" value="6ba5891a-f9c9-4761-ab6a-d18c8d0ba17f" />
    <!-- Google Tag Manager -->
    <script>
      (function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{"gtm.start":new Date().getTime(),event:"gtm.js"}});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!="dataLayer"?"&l="+l:"";j.async=true;j.src="https://www.googletagmanager.com/gtm.js?id="+i+dl;f.parentNode.insertBefore(j,f);}})(window,document,"script","dataLayer","GTM-KKFQCVJN");
    </script>
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3905545850662775" crossorigin="anonymous"></script>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-CTYVD72Y6N"></script>
    <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","G-CTYVD72Y6N");</script>
    <script src="https://analytics.ahrefs.com/analytics.js" data-key="lWObxfdoZjQb2mgJLFkKHA" async></script>
    <script type="application/ld+json">{json.dumps(article_schema)}</script>
    <script type="application/ld+json">{json.dumps(breadcrumb_schema)}</script>
    {faq_schema}
</head>
<body>
    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-KKFQCVJN" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
    <nav id="navbar">
        <div class="nav-container">
            <a href="/" class="logo" onclick="navigateTo('/'); return false;">
                <span class="logo-icon">TP</span>
                <span class="logo-text">TopPicksOnline</span>
            </a>
            <ul class="nav-menu" id="nav-menu"></ul>
            <div class="nav-actions">
                <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle theme">
                    <svg class="theme-icon-light" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
                    <svg class="theme-icon-dark" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
                </button>
                <a href="#newsletter-footer" class="nav-cta-btn">Subscribe</a>
                <button class="mobile-menu-toggle" id="mobile-menu-toggle" onclick="toggleMobileMenu()" aria-label="Menu">
                    <svg class="menu-icon-open" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
                    <svg class="menu-icon-close" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:none;"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
            </div>
        </div>
    </nav>
    <main id="main-content">
        <article class="article-container">
            <div class="breadcrumbs" aria-label="Breadcrumb">
                <a href="/">Home</a>
                <span class="breadcrumb-sep">›</span>
                {f'<a href="/category/{re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")}">{escape(category)}</a><span class="breadcrumb-sep">›</span>' if category else ''}
                <span class="breadcrumb-current">{escape(title)}</span>
            </div>
            <header class="article-header">
                <h1 class="article-title">{escape(title)}</h1>
                <div class="meta-chips">
                    <span>{escape(author)}</span> · 
                    <span>{escape(date)}</span> · 
                    <span>{escape(read_time)}</span>
                    {f' · <span>{escape(category)}</span>' if category else ''}
                </div>
                <div class="fact-check-badge">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                    <span>Fact Checked by Editorial Team</span>
                </div>
                <div class="article-cover">
                    <img src="{image}" alt="{escape(title)}" onerror="this.style.display='none'" />
                </div>
            </header>
            <div class="article-content">
                {article_body}
            </div>
            <div class="author-bio-box">
                <div class="author-bio-avatar">{author[0].upper() if author else 'T'}</div>
                <div class="author-bio-info">
                    <div class="author-bio-name">Written by {escape(author)}</div>
                    <p class="author-bio-desc">Our editorial team researches and fact-checks every article to ensure you get accurate, actionable advice for a healthier lifestyle on a budget.</p>
                </div>
            </div>
        </article>
    </main>
    <section class="newsletter-section" id="newsletter-footer">
        <div class="newsletter-content">
            <h3 class="newsletter-title">Stay in the loop</h3>
            <p class="newsletter-description">Get weekly tips on fitness, productivity, and saving money. No spam, unsubscribe anytime.</p>
            <form class="newsletter-form" data-form-id="footer-prerender">
                <input type="email" class="newsletter-input" placeholder="Your email address" required autocomplete="email" />
                <button type="submit" class="newsletter-button" data-original-text="Subscribe">Subscribe</button>
            </form>
            <div class="newsletter-success" id="success-footer-prerender"></div>
            <div class="newsletter-error" id="error-footer-prerender"></div>
        </div>
    </section>
    <footer id="footer">
        <div class="footer-content" id="footer-content"></div>
        <div class="footer-legal">
            <a href="/privacy-policy">Privacy Policy</a>
            <span class="footer-legal-sep">&middot;</span>
            <a href="/terms">Terms of Service</a>
            <span class="footer-legal-sep">&middot;</span>
            <span>&copy; 2026 TopPicksOnline. All rights reserved.</span>
        </div>
    </footer>
</body>
</html>'''
    
    return page_html


def main():
    """Generate static HTML for every article."""
    
    if not os.path.exists(ARTICLES_DIR):
        print(f"ERROR: Articles directory not found: {ARTICLES_DIR}")
        return
    
    article_files = [f for f in os.listdir(ARTICLES_DIR) if f.endswith('.json')]
    print(f"Found {len(article_files)} articles to pre-render\n")
    
    generated = 0
    errors = 0
    
    for filename in article_files:
        slug = filename.replace('.json', '')
        filepath = os.path.join(ARTICLES_DIR, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                article_data = json.load(f)
            
            # Generate HTML
            page_html = render_article_html(article_data, slug)
            
            # Create output directory: /articles/{slug}/index.html
            output_dir = os.path.join(OUTPUT_BASE, 'articles', slug)
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(output_dir, 'index.html')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            
            generated += 1
            print(f"  [OK] /articles/{slug}/index.html")
            
        except Exception as e:
            errors += 1
            print(f"  [ERR] {slug}: {e}")
    
    print(f"\n{'='*50}")
    print(f"Pre-rendering complete!")
    print(f"  Generated: {generated}")
    print(f"  Errors: {errors}")
    print(f"  Output: /articles/*/index.html")
    print(f"\nThese static HTML files will be served by Netlify")
    print(f"before the SPA redirect catches them.")


if __name__ == '__main__':
    main()
