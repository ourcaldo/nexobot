#!/usr/bin/env python3
"""
Nexobot - Article Scraper
Entry point for the command-line interface.

Usage:
    python run.py --url "https://example.com/article"
    python run.py --config config.json
    python run.py --sitemap --sitemap-url "https://example.com/sitemap.xml"
"""

from nexobot.cli import main

if __name__ == "__main__":
    main()
