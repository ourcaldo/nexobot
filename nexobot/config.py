"""
Configuration and state management.
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class AirtableConfig:
    """Airtable integration settings."""
    api_key: str = ""
    base_id: str = ""
    table_id: str = ""
    
    @property
    def is_configured(self) -> bool:
        """Check if all required fields are set."""
        return bool(self.api_key and self.base_id and self.table_id)


@dataclass
class ScraperConfig:
    """Configuration settings loaded from config.json."""
    output_format: str = "json"
    timeout: int = 60
    prevent_duplicates: bool = True
    worker_mode: bool = False
    cycle_delay: int = 3600  # 1 hour default
    urls: List[str] = field(default_factory=list)
    airtable: Optional[AirtableConfig] = None
    
    @classmethod
    def load(cls, path: str = "config.json") -> "ScraperConfig":
        """Load configuration from JSON file."""
        if not os.path.exists(path):
            print(f"[INFO] No config file found at {path}, using defaults")
            return cls()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load Airtable config if present
            airtable_config = None
            if 'airtable' in data:
                at = data['airtable']
                airtable_config = AirtableConfig(
                    api_key=at.get('api_key', ''),
                    base_id=at.get('base_id', ''),
                    table_id=at.get('table_id', '')
                )
            
            return cls(
                output_format=data.get('output_format', 'json'),
                timeout=data.get('timeout', 60),
                prevent_duplicates=data.get('prevent_duplicates', True),
                worker_mode=data.get('worker_mode', False),
                cycle_delay=data.get('cycle_delay', 3600),
                urls=data.get('urls', []),
                airtable=airtable_config
            )
        except (json.JSONDecodeError, IOError) as e:
            print(f"[ERROR] Failed to load config: {e}")
            return cls()
    
    def save(self, path: str = "config.json"):
        """Save current configuration to JSON file."""
        data = {
            'output_format': self.output_format,
            'timeout': self.timeout,
            'prevent_duplicates': self.prevent_duplicates,
            'urls': self.urls
        }
        
        if self.airtable:
            data['airtable'] = {
                'api_key': self.airtable.api_key,
                'base_id': self.airtable.base_id,
                'table_id': self.airtable.table_id
            }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"[INFO] Config saved to {path}")


class HistoryManager:
    """Manages scraped URL history to prevent duplicate scraping."""
    
    def __init__(self, history_file: str = "scraped_history.json"):
        self.history_file = history_file
        self.scraped_urls: set = set()
        self._load_history()
    
    def _load_history(self):
        """Load scraped URL history from file."""
        if not os.path.exists(self.history_file):
            return
            
        # Fix for Docker mounting directory instead of file
        if os.path.isdir(self.history_file):
            try:
                import shutil
                print(f"[WARNING] History file is a directory. Removing and recreating as file.")
                shutil.rmtree(self.history_file)
                # Save empty history immediately to create the file
                self._save_history()
                return
            except OSError as e:
                print(f"[ERROR] Could not fix history directory: {e}")
                return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.scraped_urls = set(data.get('urls', []))
            print(f"[INFO] Loaded {len(self.scraped_urls)} URLs from history")
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARNING] Could not load history: {e}")
    
    def _save_history(self):
        """Save scraped URL history to file."""
        data = {
            'urls': list(self.scraped_urls),
            'last_updated': datetime.now().isoformat()
        }
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def is_scraped(self, url: str) -> bool:
        """Check if a URL has already been scraped."""
        return url in self.scraped_urls
    
    def mark_scraped(self, url: str):
        """Mark a URL as scraped and save to history."""
        self.scraped_urls.add(url)
        self._save_history()
    
    def clear_history(self):
        """Clear all scraped URL history."""
        self.scraped_urls.clear()
        self._save_history()
        print("[INFO] History cleared")
