"""
Data models for article content.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import json


@dataclass
class ContentSection:
    """Represents a section of article content."""
    heading: str
    content: str
    level: int = 2  # 0 for intro, 2 for h2, 3 for h3, etc.


@dataclass
class ArticleContent:
    """Represents a complete scraped article."""
    url: str
    title: str
    author: str = "Unknown"
    publish_date: str = "Unknown"
    category: str = "Unknown"
    meta_description: str = ""
    content_html: str = ""
    sections: List[ContentSection] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'url': self.url,
            'title': self.title,
            'author': self.author,
            'publish_date': self.publish_date,
            'category': self.category,
            'meta_description': self.meta_description,
            'content': self.content_html,
            'sections': [
                {
                    'heading': s.heading if s.heading else None,
                    'content': s.content,
                    'level': s.level
                }
                for s in self.sections
            ],
            'tags': self.tags,
            'scraped_at': self.scraped_at
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def to_text(self) -> str:
        """Convert to plain text format."""
        lines = [
            f"Title: {self.title}",
            f"URL: {self.url}",
            f"Author: {self.author}",
            f"Date: {self.publish_date}",
            f"Category: {self.category}",
            "",
            "=" * 60,
            ""
        ]
        
        for section in self.sections:
            if section.heading:
                lines.append(f"\n## {section.heading}\n")
            lines.append(section.content)
        
        return "\n".join(lines)
    
    def to_markdown(self) -> str:
        """Convert to Markdown format."""
        lines = [
            f"# {self.title}",
            "",
            f"**URL:** {self.url}",
            f"**Author:** {self.author}",
            f"**Date:** {self.publish_date}",
            f"**Category:** {self.category}",
            "",
            "---",
            ""
        ]
        
        for section in self.sections:
            if section.heading:
                prefix = "#" * (section.level + 1)
                lines.append(f"\n{prefix} {section.heading}\n")
            lines.append(section.content)
        
        return "\n".join(lines)
