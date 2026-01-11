"""
Content extraction logic for articles.
"""

import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from .models import ContentSection


class ContentExtractor:
    """Extracts content, metadata, and tags from HTML pages."""
    
    # Priority selectors for finding main content
    CONTENT_SELECTORS = [
        'div.elementor-widget-theme-post-content',  # Elementor
        'div.entry-content',                        # WordPress standard
        'div.post-content',                         # Generic blog
        'div.article-content',                      # Generic article
        'div.td-post-content',                      # Theme Developer theme
        'div.blog-post-content',                    # Generic
        'div.single-post-content',                  # Single post themes
    ]
    
    # Classes to exclude from content detection
    EXCLUDE_CLASSES = [
        'toc', 'table-of-contents', 'widget', 'sidebar', 
        'menu', 'nav', 'header', 'footer', 'related', 'comment'
    ]
    
    def extract_meta(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract Open Graph and meta description."""
        meta = {
            'og_title': '',
            'og_image': '',
            'description': '',
        }
        
        og_title = soup.find('meta', property='og:title')
        if og_title:
            meta['og_title'] = og_title.get('content', '')
        
        og_image = soup.find('meta', property='og:image')
        if og_image:
            meta['og_image'] = og_image.get('content', '')
        
        description = soup.find('meta', attrs={'name': 'description'})
        if description:
            meta['description'] = description.get('content', '')
        
        return meta
    
    def extract_article_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract author, category, and date from the page."""
        info = {
            'author': 'Unknown',
            'category': 'Unknown',
            'date': 'Unknown',
        }
        
        # Try to find author
        author_elem = soup.find('a', class_=lambda c: c and 'author' in c.lower() if c else False)
        if author_elem:
            info['author'] = author_elem.get_text(strip=True)
        
        # Try to find category
        cat_elem = soup.find('a', rel='category tag') or soup.find('a', class_=lambda c: c and 'category' in c.lower() if c else False)
        if cat_elem:
            info['category'] = cat_elem.get_text(strip=True)
        
        # Try to find date
        date_pattern = r'(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{1,2},\s+\d{4}'
        page_text = soup.get_text()
        date_match = re.search(date_pattern, page_text)
        if date_match:
            info['date'] = date_match.group(0)
        
        return info
    
    def extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract article tags using multiple strategies."""
        tags = set()
        
        # Strategy A: Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords = meta_keywords['content'].split(',')
            for kw in keywords:
                kw = kw.strip()
                if kw:
                    tags.add(kw)
        
        # Strategy B: Meta article:tag
        for meta_tag in soup.find_all('meta', attrs={'property': 'article:tag'}):
            if meta_tag.get('content'):
                tags.add(meta_tag['content'].strip())
        
        # Strategy C: Visible tag links
        for link in soup.find_all('a', rel='tag'):
            tag_text = link.get_text(strip=True)
            if tag_text:
                tags.add(tag_text)
        
        # Strategy D: Links in tag containers
        tag_containers = soup.find_all(['div', 'span', 'ul'], 
            class_=lambda c: c and 'tag' in c.lower() if c else False)
        for container in tag_containers:
            for link in container.find_all('a'):
                tag_text = link.get_text(strip=True)
                if tag_text and len(tag_text) < 50:
                    tags.add(tag_text)
        
        return list(tags)
    
    def extract_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract main article content."""
        content = {
            'title': '',
            'content_html': '',
            'sections': [],
        }
        
        # Find the main title
        h1 = soup.find('h1')
        if h1:
            content['title'] = h1.get_text(strip=True)
        
        # Find main content area using priority selectors
        article = self._find_content_area(soup)
        
        if article:
            content['content_html'] = self._extract_html_content(article)
            content['sections'] = self._extract_sections(article)
        
        return content
    
    def _find_content_area(self, soup: BeautifulSoup):
        """Find the main content area using priority selectors."""
        # Priority 1: Specific CMS classes
        for selector in self.CONTENT_SELECTORS:
            article = soup.select_one(selector)
            if article:
                return article
        
        # Priority 2: Semantic <article> tag (pick largest)
        articles = soup.find_all('article')
        if articles:
            return max(articles, key=lambda a: len(a.get_text()))
        
        # Priority 3: Fuzzy search for 'content' class with exclusions
        def is_content_div(tag):
            if tag.name != 'div':
                return False
            classes = tag.get('class')
            if not classes:
                return False
            class_str = ' '.join(classes).lower()
            if 'content' not in class_str:
                return False
            if any(ex in class_str for ex in self.EXCLUDE_CLASSES):
                return False
            return True
        
        article = soup.find(is_content_div)
        if article:
            return article
        
        # Fallback to <main> or <body>
        return soup.find('main') or soup.body
    
    def _extract_html_content(self, article) -> str:
        """Extract content as HTML."""
        if not article:
            return ""
        
        html_parts = []
        allowed_tags = ['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 
                       'strong', 'em', 'br', 'blockquote']
        
        for element in article.find_all(['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'table', 'blockquote']):
            if element.name in allowed_tags:
                clean_elem = self._clean_html_element(element)
                if clean_elem:
                    html_parts.append(clean_elem)
        
        return "\n".join(html_parts)
    
    def _clean_html_element(self, element) -> str:
        """Clean an HTML element, keeping only text."""
        tag_name = element.name
        
        if tag_name in ['p', 'h2', 'h3', 'h4', 'blockquote']:
            text = element.get_text(strip=True)
            if text:
                return f"<{tag_name}>{text}</{tag_name}>"
            return ""
        
        if tag_name in ['ul', 'ol']:
            items = element.find_all('li')
            list_html = ''.join([f"<li>{li.get_text(strip=True)}</li>" for li in items])
            return f"<{tag_name}>{list_html}</{tag_name}>"
        
        if tag_name == 'table':
            return self._extract_table_html(element)
        
        return ""
    
    def _extract_table_html(self, table) -> str:
        """Convert table to clean HTML."""
        rows_html = []
        for tr in table.find_all('tr'):
            cells = [f"<td>{td.get_text(strip=True)}</td>" for td in tr.find_all(['td', 'th'])]
            if cells:
                rows_html.append(f"<tr>{''.join(cells)}</tr>")
        return f"<table>{''.join(rows_html)}</table>"
    
    def _extract_sections(self, article) -> List[ContentSection]:
        """Extract content as plain text sections."""
        intro_parts = []
        current_section = None
        sections = []
        
        for element in article.find_all(['p', 'h2', 'h3', 'ul', 'ol', 'table']):
            if element.name == 'h2':
                heading_text = element.get_text(strip=True)
                
                if current_section and current_section.content.strip():
                    sections.append(current_section)
                
                current_section = ContentSection(
                    heading=heading_text,
                    content='',
                    level=2
                )
                
            elif element.name == 'h3' and current_section:
                current_section.content += f"\n\n### {element.get_text(strip=True)}\n"
                
            elif element.name == 'p':
                text = element.get_text(strip=True)
                if text:
                    if current_section is None:
                        intro_parts.append(text)
                    else:
                        current_section.content += f"\n{text}"
                        
            elif element.name in ['ul', 'ol']:
                items = element.find_all('li')
                list_text = "\n".join([f"  • {li.get_text(strip=True)}" for li in items])
                if current_section:
                    current_section.content += f"\n{list_text}"
                else:
                    intro_parts.append(list_text)
                    
            elif element.name == 'table':
                table_text = self._extract_table_text(element)
                if current_section:
                    current_section.content += f"\n\n{table_text}\n"
        
        if current_section and current_section.content.strip():
            sections.append(current_section)
        
        # Build final sections with introduction first
        all_sections = []
        intro_text = "\n\n".join(intro_parts)
        if intro_text.strip():
            all_sections.append(ContentSection(
                heading="",
                content=intro_text,
                level=0
            ))
        all_sections.extend(sections)
        
        return all_sections
    
    def _extract_table_text(self, table) -> str:
        """Convert table to plain text."""
        rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if cells:
                rows.append(" | ".join(cells))
        return "\n".join(rows)
