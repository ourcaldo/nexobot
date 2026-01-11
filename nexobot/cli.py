"""
Command-line interface for Nexobot scraper.
"""

import argparse
import time

from .scraper import Scraper
from .storage import ArticleStorage
from .config import ScraperConfig, HistoryManager
from .sitemap import discover_sitemap


def main():
    """Main entry point for the scraper CLI."""
    parser = argparse.ArgumentParser(
        description='Nexobot - Article Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --url "https://example.com/article"
  python run.py --config config.json
  python run.py --sitemap --sitemap-url "https://example.com/sitemap.xml"
        """
    )
    
    parser.add_argument('--url', '-u', help='Single URL to scrape')
    parser.add_argument('--config', '-c', help='Path to config.json file')
    parser.add_argument('--sitemap', '-s', action='store_true', 
                        help='Scrape from sitemap')
    parser.add_argument('--sitemap-url', help='Direct sitemap URL')
    parser.add_argument('--max', '-m', type=int, default=None,
                        help='Maximum articles to scrape (default: all)')
    parser.add_argument('--delay', '-d', type=float, default=1.0,
                        help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--output', '-o', default='output',
                        help='Output directory (default: output)')
    parser.add_argument('--min-depth', type=int, default=3,
                        help='Minimum URL path depth (default: 3)')
    parser.add_argument('--skip-validation', action='store_true',
                        help='Skip URL validation')
    
    args = parser.parse_args()
    
    # Initialize scraper and storage
    scraper = Scraper(min_path_depth=args.min_depth)
    storage = ArticleStorage(args.output)
    
    # Config mode
    if args.config:
        _run_config_mode(args, scraper, storage)
        return
    
    # Sitemap mode
    if args.sitemap:
        _run_sitemap_mode(args, scraper, storage)
        return
    
    # Single URL mode
    _run_single_mode(args, scraper, storage)


def _run_config_mode(args, scraper: Scraper, storage: ArticleStorage):
    """Process URLs from config.json."""
    config = ScraperConfig.load(args.config)
    
    # Check for worker mode (daemon)
    if config.worker_mode:
        from .worker import WorkerManager
        
        print("[INFO] Starting worker mode (daemon)")
        print(f"[INFO] Cycle delay: {config.cycle_delay}s")
        
        manager = WorkerManager(config, output_dir=args.output)
        manager.start(
            cycle_delay=config.cycle_delay,
            request_delay=args.delay,
            max_articles=args.max
        )
        return
    
    # Normal config mode (single run)
    config = ScraperConfig.load(args.config)
    history = HistoryManager() if config.prevent_duplicates else None
    
    # Create storage with Airtable config if present
    storage = ArticleStorage(args.output, airtable_config=config.airtable)
    output_format = config.output_format
    
    print(f"[INFO] Loaded config with {len(config.urls)} URLs")
    print(f"[INFO] Output format: {output_format}")
    
    for url in config.urls:
        if history and history.is_scraped(url):
            print(f"[SKIP] Already scraped: {url}")
            continue
        
        if scraper.url_validator.is_root_domain(url):
            print(f"\n[INFO] Root domain: {url}")
            sitemap_url = discover_sitemap(url)
            if sitemap_url:
                articles = scraper.scrape_from_sitemap(
                    sitemap_url=sitemap_url,
                    max_articles=args.max,
                    delay=args.delay
                )
                for article in articles:
                    if history and history.is_scraped(article.url):
                        continue
                    storage.save(article, output_format=output_format)
                    if history:
                        history.mark_scraped(article.url)
            else:
                print(f"[FAILED] No sitemap found for {url}")
        else:
            article = scraper.scrape(url, validate_url=not args.skip_validation)
            if article:
                storage.save(article, output_format=output_format)
                if history:
                    history.mark_scraped(url)
        
        time.sleep(args.delay)


def _run_sitemap_mode(args, scraper: Scraper, storage: ArticleStorage):
    """Scrape from sitemap."""
    articles = scraper.scrape_from_sitemap(
        sitemap_url=args.sitemap_url,
        max_articles=args.max,
        delay=args.delay
    )
    for article in articles:
        storage.save(article)


def _run_single_mode(args, scraper: Scraper, storage: ArticleStorage):
    """Scrape a single URL."""
    url = args.url or "https://cetta.id/updates/bahasa-jepang/kata-karena/"
    
    if scraper.url_validator.is_root_domain(url):
        print(f"[INFO] Root domain detected: {url}")
        print(f"[INFO] Auto-discovering sitemap...")
        
        sitemap_url = discover_sitemap(url)
        if sitemap_url:
            print(f"[INFO] Found sitemap, switching to sitemap mode")
            articles = scraper.scrape_from_sitemap(
                sitemap_url=sitemap_url,
                max_articles=args.max,
                delay=args.delay
            )
            for article in articles:
                storage.save(article)
        else:
            print(f"[FAILED] Could not find sitemap for {url}")
    else:
        article = scraper.scrape(url, validate_url=not args.skip_validation)
        if article:
            storage.save(article)
            print("\n" + "=" * 60)
            print("SCRAPED CONTENT (JSON)")
            print("=" * 60)
            print(article.to_json())
        else:
            print("[FAILED] Could not scrape the article")


if __name__ == "__main__":
    main()
