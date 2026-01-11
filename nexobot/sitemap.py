"""
Sitemap parsing and discovery.
"""

import re
import requests
from typing import List, Optional, Generator
from dataclasses import dataclass
from bs4 import BeautifulSoup


@dataclass
class SitemapEntry:
    """Represents a single URL entry from a sitemap."""
    url: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None


class SitemapParser:
    """Parser for XML sitemaps with support for sitemap indexes."""
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/xml,text/xml,*/*',
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def fetch_sitemap(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a sitemap XML."""
        try:
            print(f"[INFO] Fetching sitemap: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml-xml')
        except requests.RequestException as e:
            print(f"[ERROR] Failed to fetch sitemap: {e}")
            return None
    
    def is_sitemap_index(self, soup: BeautifulSoup) -> bool:
        """Check if the sitemap is a sitemap index."""
        return soup.find('sitemapindex') is not None
    
    def parse_sitemap_index(self, soup: BeautifulSoup) -> List[str]:
        """Extract sitemap URLs from a sitemap index."""
        sitemaps = []
        for sitemap in soup.find_all('sitemap'):
            loc = sitemap.find('loc')
            if loc:
                sitemaps.append(loc.get_text(strip=True))
        return sitemaps
    
    def parse_urlset(self, soup: BeautifulSoup) -> List[SitemapEntry]:
        """Extract URL entries from a regular sitemap."""
        entries = []
        for url_elem in soup.find_all('url'):
            loc = url_elem.find('loc')
            if not loc:
                continue
            
            entry = SitemapEntry(url=loc.get_text(strip=True))
            
            lastmod = url_elem.find('lastmod')
            if lastmod:
                entry.lastmod = lastmod.get_text(strip=True)
            
            changefreq = url_elem.find('changefreq')
            if changefreq:
                entry.changefreq = changefreq.get_text(strip=True)
            
            priority = url_elem.find('priority')
            if priority:
                try:
                    entry.priority = float(priority.get_text(strip=True))
                except ValueError:
                    pass
            
            entries.append(entry)
        
        return entries
    
    def get_all_urls(self, sitemap_url: str, 
                     url_filter: Optional[str] = None,
                     max_urls: Optional[int] = None) -> Generator[SitemapEntry, None, None]:
        """
        Get all URLs from a sitemap, handling indexes recursively.
        
        Args:
            sitemap_url: URL of the sitemap
            url_filter: Optional regex pattern to filter URLs
            max_urls: Maximum number of URLs to return
        
        Yields:
            SitemapEntry objects
        """
        count = 0
        pattern = re.compile(url_filter) if url_filter else None
        
        soup = self.fetch_sitemap(sitemap_url)
        if not soup:
            return
        
        if self.is_sitemap_index(soup):
            print(f"[INFO] Found sitemap index with nested sitemaps")
            child_sitemaps = self.parse_sitemap_index(soup)
            
            # Smart filtering: If we see sitemaps with "post" in the name, 
            # we prioritize them and ignore others (like page, category, etc.)
            post_sitemaps = [url for url in child_sitemaps if 'post' in url.lower().split('/')[-1]]
            
            target_sitemaps = post_sitemaps if post_sitemaps else child_sitemaps
            
            if post_sitemaps:
                print(f"[INFO] Filtering for post sitemaps only ({len(post_sitemaps)} found)")
            
            for child_sitemap_url in target_sitemaps:
                if max_urls and count >= max_urls:
                    break
                
                # Skip known non-content sitemaps if we didn't explicitly filter for posts
                if not post_sitemaps:
                    ignore_keywords = ['category', 'tag', 'author', 'user', 'page']
                    if any(k in child_sitemap_url.lower() for k in ignore_keywords):
                        continue

                child_soup = self.fetch_sitemap(child_sitemap_url)
                if child_soup:
                    for entry in self.parse_urlset(child_soup):
                        if max_urls and count >= max_urls:
                            break
                        if pattern and not pattern.search(entry.url):
                            continue
                        yield entry
                        count += 1
        else:
            for entry in self.parse_urlset(soup):
                if max_urls and count >= max_urls:
                    break
                if pattern and not pattern.search(entry.url):
                    continue
                yield entry
                count += 1
        
        print(f"[INFO] Found {count} URLs matching criteria")


def discover_sitemap(base_url: str) -> Optional[str]:
    """
    Try to discover the sitemap URL for a website.
    Checks common locations like /sitemap.xml, /sitemap_index.xml, etc.
    """
    common_paths = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/sitemap-index.xml',
        '/post-sitemap.xml',
        '/page-sitemap.xml',
        '/wp-sitemap.xml',
    ]
    
    base_url = base_url.rstrip('/')
    
    for path in common_paths:
        url = base_url + path
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                print(f"[INFO] Found sitemap at: {url}")
                return url
        except requests.RequestException:
            continue
    
    print(f"[WARNING] Could not find sitemap for {base_url}")
    return None
