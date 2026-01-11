"""
Storage utilities for saving scraped articles.
"""

import os
import json
from datetime import datetime
from typing import Optional

from .models import ArticleContent
from .config import AirtableConfig


class ArticleStorage:
    """Handles saving articles to various formats including Airtable."""
    
    def __init__(self, output_dir: str = "output", airtable_config: Optional[AirtableConfig] = None):
        self.output_dir = output_dir
        self.airtable_config = airtable_config
        self._airtable_client = None
        os.makedirs(output_dir, exist_ok=True)
    
    @property
    def airtable_client(self):
        """Lazy-load Airtable client."""
        if self._airtable_client is None and self.airtable_config and self.airtable_config.is_configured:
            from .integrations.airtable import AirtableClient
            self._airtable_client = AirtableClient(
                api_key=self.airtable_config.api_key,
                base_id=self.airtable_config.base_id,
                table_id=self.airtable_config.table_id
            )
        return self._airtable_client
    
    def _generate_filename(self, article: ArticleContent, ext: str) -> str:
        """Generate a unique filename based on article title."""
        safe_title = "".join(c for c in article.title if c.isalnum() or c in (' ', '-', '_'))
        safe_title = safe_title.replace(' ', '_')[:50]
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{safe_title}_{timestamp}.{ext}"
    
    def save(self, article: ArticleContent, output_format: str = "json") -> bool:
        """
        Save article to specified format.
        
        Args:
            article: ArticleContent to save
            output_format: 'json', 'txt', 'md', or 'airtable'
        
        Returns:
            True if saved successfully
        """
        if output_format == 'airtable':
            return self._save_to_airtable(article)
        elif output_format == 'json':
            return self._save_json(article) is not None
        elif output_format == 'txt':
            return self._save_text(article) is not None
        elif output_format == 'md':
            return self._save_markdown(article) is not None
        else:
            print(f"[WARNING] Unknown output format: {output_format}, using json")
            return self._save_json(article) is not None
    
    def _save_to_airtable(self, article: ArticleContent) -> bool:
        """Save article to Airtable."""
        if not self.airtable_client:
            print("[ERROR] Airtable not configured")
            return False
        
        record_id = self.airtable_client.create_record(article)
        return record_id is not None
    
    def _save_json(self, article: ArticleContent) -> str:
        """Save article as JSON."""
        filename = self._generate_filename(article, 'json')
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(article.to_json())
        
        print(f"[SAVED] {filepath}")
        return filepath
    
    def _save_text(self, article: ArticleContent) -> str:
        """Save article as plain text."""
        filename = self._generate_filename(article, 'txt')
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(article.to_text())
        
        print(f"[SAVED] {filepath}")
        return filepath
    
    def _save_markdown(self, article: ArticleContent) -> str:
        """Save article as Markdown."""
        filename = self._generate_filename(article, 'md')
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(article.to_markdown())
        
        print(f"[SAVED] {filepath}")
        return filepath
