"""
URL validation logic for distinguishing articles from archive pages.
"""

import re
from urllib.parse import urlparse, parse_qs


class URLValidator:
    """
    Validates URLs to distinguish single posts from archive/listing pages.
    
    Single posts typically have:
    - Deeper URL paths (e.g., /blog/category/slug)
    - No pagination parameters
    - A slug at the end (not just category)
    
    Archive pages typically have:
    - Shallow paths (e.g., /blog or /blog/category)
    - Pagination (page/2, ?page=2)
    - Category/tag listing pages
    """
    
    # Common archive/listing path patterns to exclude
    ARCHIVE_PATTERNS = [
        r'^/page/\d+/?$',                    # /page/2
        r'^/[^/]+/?$',                       # /updates (single segment = archive)
        r'^/[^/]+/page/\d+/?$',              # /blog/page/2
        r'^/category/',                      # /category/something
        r'^/tag/',                           # /tag/something
        r'^/author/',                        # /author/someone
        r'^/archive/',                       # /archive/
        r'^/search',                         # /search?q=
        r'/feed/?$',                         # RSS feeds
        r'\.(xml|rss)$',                     # sitemap.xml, feed.rss
    ]
    
    # Pagination query parameters
    PAGINATION_PARAMS = ['page', 'paged', 'p', 'offset']
    
    # Common subdomains that indicate blog/article hosting
    BLOG_SUBDOMAINS = ['blog', 'news', 'articles', 'content']
    
    def __init__(self, min_path_depth: int = 3):
        """
        Args:
            min_path_depth: Minimum URL path segments for a valid single post.
                           e.g., /updates/category/slug = 3 segments
        """
        self.min_path_depth = min_path_depth
        self.archive_patterns = [re.compile(p, re.IGNORECASE) for p in self.ARCHIVE_PATTERNS]
    
    def get_path_depth(self, url: str) -> int:
        """Count the number of path segments in a URL."""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if not path:
            return 0
        return len(path.split('/'))
    
    def has_pagination(self, url: str) -> bool:
        """Check if URL has pagination parameters."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        for param in self.PAGINATION_PARAMS:
            if param in query_params:
                return True
        
        # Also check for /page/N in path
        if re.search(r'/page/\d+', parsed.path):
            return True
        
        return False
    
    def matches_archive_pattern(self, url: str) -> bool:
        """Check if URL matches common archive patterns."""
        parsed = urlparse(url)
        path = parsed.path
        
        # Check if URL has a blog-style subdomain
        is_subdomain = self.has_subdomain(url)
        
        for i, pattern in enumerate(self.archive_patterns):
            # Skip single-segment pattern (index 1) for subdomain URLs
            if i == 1 and is_subdomain:
                continue
            if pattern.search(path):
                return True
        
        return False
    
    def is_root_domain(self, url: str) -> bool:
        """Check if URL is a root domain (no path, or just /)."""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        return not path and not parsed.query
    
    def has_subdomain(self, url: str) -> bool:
        """Check if URL has a subdomain like blog.site.com."""
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        
        parts = hostname.split('.')
        if len(parts) >= 3:
            subdomain = parts[0]
            if subdomain != 'www' and subdomain in self.BLOG_SUBDOMAINS:
                return True
        
        return False
    
    def is_single_post(self, url: str) -> tuple[bool, str]:
        """
        Determine if a URL is likely a single post.
        
        Returns:
            Tuple of (is_valid, reason)
        """
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        # Check 0: If it's a root domain, it's not a single post
        if self.is_root_domain(url):
            return False, "URL is a root domain (use sitemap discovery)"
        
        # Check 1: Has pagination = not a single post
        if self.has_pagination(url):
            return False, "URL has pagination parameters"
        
        # Check 2: Matches archive pattern
        if self.matches_archive_pattern(url):
            return False, "URL matches archive pattern"
        
        # Check 3: Path depth check (adjusted for subdomains)
        depth = self.get_path_depth(url)
        min_depth = 1 if self.has_subdomain(url) else self.min_path_depth
        
        if depth < min_depth:
            return False, f"URL path too shallow ({depth} segments, need {min_depth})"
        
        # Check 4: Ends with a slug (has text after last /)
        path_parts = path.split('/')
        last_segment = path_parts[-1] if path_parts else ''
        
        if not last_segment or last_segment.isdigit():
            return False, "URL doesn't end with a valid slug"
        
        return True, "Valid single post URL"
