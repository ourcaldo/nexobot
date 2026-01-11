"""
Worker system for continuous parallel scraping.
One worker per unique domain, running independently.
"""

import threading
import signal
import time
from urllib.parse import urlparse
from typing import Dict, List, Optional
from collections import defaultdict

from .scraper import Scraper
from .storage import ArticleStorage
from .config import ScraperConfig, HistoryManager
from .sitemap import discover_sitemap


class DomainWorker(threading.Thread):
    """Worker thread that handles all URLs for a single domain."""
    
    def __init__(self, 
                 domain: str,
                 urls: List[str],
                 scraper: Scraper,
                 storage: ArticleStorage,
                 history: Optional[HistoryManager],
                 output_format: str,
                 cycle_delay: int = 3600,
                 request_delay: float = 1.0,
                 max_articles: Optional[int] = None):
        super().__init__(daemon=True)
        self.domain = domain
        self.urls = urls
        self.scraper = scraper
        self.storage = storage
        self.history = history
        self.output_format = output_format
        self.cycle_delay = cycle_delay
        self.request_delay = request_delay
        self.max_articles = max_articles
        self.running = True
        self.name = f"Worker-{domain}"
    
    def stop(self):
        """Signal the worker to stop."""
        self.running = False
    
    def run(self):
        """Main worker loop - runs forever until stopped."""
        print(f"[{self.name}] Started with {len(self.urls)} URL(s)")
        
        cycle = 0
        while self.running:
            cycle += 1
            print(f"\n[{self.name}] Starting cycle {cycle}")
            
            try:
                self._process_urls()
            except Exception as e:
                print(f"[{self.name}] Error in cycle {cycle}: {e}")
            
            if self.running:
                print(f"[{self.name}] Cycle {cycle} complete. Sleeping {self.cycle_delay}s...")
                # Sleep in small chunks to allow quick shutdown
                for _ in range(self.cycle_delay):
                    if not self.running:
                        break
                    time.sleep(1)
        
        print(f"[{self.name}] Stopped")
    
    def _process_urls(self):
        """Process all URLs for this domain."""
        for url in self.urls:
            if not self.running:
                break
            
            # Skip if already scraped
            if self.history and self.history.is_scraped(url):
                print(f"[{self.name}] Skip (already scraped): {url}")
                continue
            
            # Check logic:
            # 1. Direct sitemap (.xml)
            # 2. Root domain -> Discover sitemap
            # 3. Regular article URL
            
            if url.lower().endswith('.xml'):
                self._process_sitemap_url(url)
            elif self.scraper.url_validator.is_root_domain(url):
                self._process_sitemap(url)
            else:
                self._process_single_url(url)
            
            time.sleep(self.request_delay)
    
    def _process_sitemap(self, url: str):
        """Process a root domain via sitemap discovery."""
        print(f"[{self.name}] Discovering sitemap for {url}")
        sitemap_url = discover_sitemap(url)
        
        if not sitemap_url:
            print(f"[{self.name}] No sitemap found for {url}")
            return
        
        self._scrape_and_save_sitemap(sitemap_url)

    def _process_sitemap_url(self, sitemap_url: str):
        """Process a direct sitemap URL."""
        print(f"[{self.name}] Processing direct sitemap: {sitemap_url}")
        self._scrape_and_save_sitemap(sitemap_url)

    def _scrape_and_save_sitemap(self, sitemap_url: str):
        """Common logic to scrape articles from a sitemap URL."""
        articles = self.scraper.scrape_from_sitemap(
            sitemap_url=sitemap_url,
            max_articles=self.max_articles,
            delay=self.request_delay
        )
        
        for article in articles:
            if not self.running:
                break
            if self.history and self.history.is_scraped(article.url):
                continue
            
            self.storage.save(article, output_format=self.output_format)
            if self.history:
                self.history.mark_scraped(article.url)
    
    def _process_single_url(self, url: str):
        """Process a single article URL."""
        article = self.scraper.scrape(url, validate_url=False)
        if article:
            self.storage.save(article, output_format=self.output_format)
            if self.history:
                self.history.mark_scraped(url)


class WorkerManager:
    """Manages multiple domain workers."""
    
    def __init__(self, config: ScraperConfig, output_dir: str = "output"):
        self.config = config
        self.output_dir = output_dir
        self.workers: List[DomainWorker] = []
        self.running = False
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n[Manager] Shutdown signal received. Stopping workers...")
        self.stop()
    
    def _group_urls_by_domain(self) -> Dict[str, List[str]]:
        """Group URLs by their domain."""
        domain_urls = defaultdict(list)
        
        for url in self.config.urls:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            domain_urls[domain].append(url)
        
        return dict(domain_urls)
    
    def start(self, 
              cycle_delay: int = 3600,
              request_delay: float = 1.0,
              max_articles: Optional[int] = None):
        """Start all domain workers."""
        domain_urls = self._group_urls_by_domain()
        
        print(f"[Manager] Starting {len(domain_urls)} worker(s)")
        
        # Create shared resources
        history = HistoryManager() if self.config.prevent_duplicates else None
        
        for domain, urls in domain_urls.items():
            # Each worker gets its own scraper instance
            scraper = Scraper()
            storage = ArticleStorage(self.output_dir, airtable_config=self.config.airtable)
            
            worker = DomainWorker(
                domain=domain,
                urls=urls,
                scraper=scraper,
                storage=storage,
                history=history,
                output_format=self.config.output_format,
                cycle_delay=cycle_delay,
                request_delay=request_delay,
                max_articles=max_articles
            )
            
            self.workers.append(worker)
            worker.start()
        
        self.running = True
        
        # Keep main thread alive
        try:
            while self.running and any(w.is_alive() for w in self.workers):
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop all workers gracefully."""
        self.running = False
        
        for worker in self.workers:
            worker.stop()
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
        
        print("[Manager] All workers stopped")
