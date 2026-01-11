"""
Nexobot - Article Scraper Package

A modular content scraper for extracting articles from websites.
Supports direct URL scraping, sitemap discovery, and configuration-based batch processing.
"""

__version__ = "1.0.0"
__author__ = "Nexobot Team"

from .scraper import Scraper
from .models import ArticleContent, ContentSection
from .config import ScraperConfig, HistoryManager

__all__ = [
    "Scraper",
    "ArticleContent",
    "ContentSection",
    "ScraperConfig",
    "HistoryManager",
]
