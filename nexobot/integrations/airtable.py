"""
Airtable integration for sending scraped articles to Airtable.
"""

import requests
from typing import Optional, Dict, Any

from ..models import ArticleContent


class AirtableClient:
    """Client for Airtable API to create article records."""
    
    BASE_URL = "https://api.airtable.com/v0"
    
    def __init__(self, api_key: str, base_id: str, table_id: str):
        """
        Initialize Airtable client.
        
        Args:
            api_key: Airtable Personal Access Token (pat...)
            base_id: Airtable Base ID (app...)
            table_id: Airtable Table ID (tbl...)
        """
        self.api_key = api_key
        self.base_id = base_id
        self.table_id = table_id
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    @property
    def endpoint(self) -> str:
        """Get the API endpoint for this table."""
        return f"{self.BASE_URL}/{self.base_id}/{self.table_id}"
    
    def create_record(self, article: ArticleContent) -> Optional[str]:
        """
        Create a record in Airtable from an article.
        
        Args:
            article: ArticleContent object to save
        
        Returns:
            Record ID if successful, None otherwise
        """
        import json
        
        # Escape newlines so it's stored as single line with literal \n
        content_escaped = article.content_html.replace('\n', '\\n').replace('\r', '')
        
        # Map article fields to Airtable columns
        fields = {
            "URL": article.url,
            "Title": article.title,
            "Meta Description": article.meta_description,
            "Category": article.category,
            "Content": content_escaped,  # Escaped HTML string
            "JSON": article.to_json()
        }
        
        payload = {
            "records": [{"fields": fields}]
        }
        
        try:
            print(f"[AIRTABLE] Sending to Airtable: {article.title[:50]}...")
            response = self.session.post(self.endpoint, json=payload)
            response.raise_for_status()
            
            data = response.json()
            record_id = data["records"][0]["id"]
            print(f"[AIRTABLE] Created record: {record_id}")
            return record_id
            
        except requests.exceptions.HTTPError as e:
            print(f"[AIRTABLE ERROR] HTTP {e.response.status_code}: {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[AIRTABLE ERROR] Request failed: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"[AIRTABLE ERROR] Unexpected response format: {e}")
            return None
