"""
Main Scraper class that orchestrates the scraping workflow.
"""

import requests
import time
from typing import Optional, List
from bs4 import BeautifulSoup

from .models import ArticleContent
from .validators import URLValidator
from .extractors import ContentExtractor
from .sitemap import SitemapParser, discover_sitemap


class Scraper:
    """Main scraper class for extracting article content from websites."""
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    def __init__(self, min_path_depth: int = 3, timeout: int = 30):
        """
        Initialize the scraper.
        
        Args:
            min_path_depth: Minimum URL path segments for valid posts.
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        
        self.url_validator = URLValidator(min_path_depth=min_path_depth)
        self.extractor = ContentExtractor()
        self.sitemap_parser = SitemapParser()
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except requests.RequestException as e:
            print(f"[ERROR] Failed to fetch {url}: {e}")
            return None
    
    def is_valid_article(self, content: dict) -> tuple[bool, str]:
        """Validate that extracted content looks like an article."""
        content_html = content.get('content_html', '')
        sections = content.get('sections', [])
        
        # Check content length
        total_length = len(content_html)
        if total_length == 0:
            for section in sections:
                total_length += len(section.content)
        
        if total_length < 100:
            return False, "Content too short"
        
        return True, "Valid article"
    
    def scrape(self, url: str, validate_url: bool = True) -> Optional[ArticleContent]:
        """
        Scrape a single article from a URL.
        
        Args:
            url: The URL to scrape
            validate_url: Whether to validate the URL structure
        
        Returns:
            ArticleContent if successful, None otherwise
        """
        # Step 1: Validate URL
        if validate_url:
            is_valid, reason = self.url_validator.is_single_post(url)
            if not is_valid:
                print(f"[SKIP] {url}")
                print(f"       Reason: {reason}")
                return None
        
        print(f"[INFO] Scraping: {url}")
        
        # Step 2: Fetch page
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        # Step 3: Extract content
        meta = self.extractor.extract_meta(soup)
        info = self.extractor.extract_article_info(soup)
        content = self.extractor.extract_content(soup)
        tags = self.extractor.extract_tags(soup)
        
        # Step 4: Validate content
        is_valid, reason = self.is_valid_article(content)
        if not is_valid:
            print(f"[SKIP] {url}")
            print(f"       Reason: {reason}")
            return None
        
        article = ArticleContent(
            url=url,
            title=content['title'] or meta['og_title'],
            author=info['author'],
            publish_date=info['date'],
            category=info['category'],
            meta_description=meta['description'],
            content_html=content['content_html'],
            sections=content['sections'],
            tags=tags,
        )
        
        print(f"[SUCCESS] Scraped: {article.title}")
        return article
    
    def scrape_from_sitemap(self, 
                            sitemap_url: str = None,
                            base_url: str = "https://cetta.id",
                            url_filter: str = None,
                            max_articles: int = 10,
                            delay: float = 1.0):
        """
        Scrape multiple articles from a sitemap.
        Yields ArticleContent objects one by one.
        
        Args:
            sitemap_url: Direct URL to sitemap. If None, will try to discover.
            base_url: Base URL of the website for sitemap discovery.
            url_filter: Regex pattern to filter URLs.
            max_articles: Maximum number of articles to scrape.
            delay: Delay between requests in seconds.
        
        Yields:
            ArticleContent objects
        """
        if not sitemap_url:
            sitemap_url = discover_sitemap(base_url)
            if not sitemap_url:
                print(f"[ERROR] Could not find sitemap for {base_url}")
                return
        
        # Get all URLs from sitemap
        # If max_articles is None (scrape all), we don't limit discovery
        fetch_limit = max_articles * 3 if max_articles is not None else None
        
        all_entries = list(self.sitemap_parser.get_all_urls(
            sitemap_url, 
            url_filter=url_filter,
            max_urls=fetch_limit
        ))
        
        # Filter valid URLs
        valid_urls = []
        for entry in all_entries:
            is_valid, _ = self.url_validator.is_single_post(entry.url)
            if is_valid:
                valid_urls.append(entry)
                if max_articles is not None and len(valid_urls) >= max_articles:
                    break
        
        print(f"[INFO] Found {len(valid_urls)} valid URLs to scrape")
        
        count = 0
        for i, entry in enumerate(valid_urls, 1):
            print(f"\n[{i}/{len(valid_urls)}] Processing: {entry.url}")
            
            article = self.scrape(entry.url, validate_url=False)
            if article:
                yield article
                count += 1
            
            if i < len(valid_urls):
                time.sleep(delay)
        
        print(f"\n[COMPLETE] Scraped {count} articles successfully")
        

