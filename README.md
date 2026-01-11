# Nexobot - Article Scraper

A modular content scraper with parallel workers and Airtable integration.

## Features
- **Multi-site support**: Elementor, WordPress, and generic blogs
- **Smart URL detection**: Auto-distinguishes articles from archives
- **Sitemap discovery**: Auto-find and process sitemaps for root domains
- **Parallel workers**: One worker per domain, running independently
- **Airtable integration**: Send articles directly to Airtable
- **Duplicate prevention**: Tracks scraped URLs to avoid re-processing
- **Daemon mode**: Runs continuously, re-scraping on schedule

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Docker (Recommended)
```bash
docker-compose up -d
```

### Local
```bash
python run.py --config config.json
```

## Configuration

Create a `config.json` file:

```json
{
  "output_format": "airtable",
  "timeout": 60,
  "prevent_duplicates": true,
  "worker_mode": true,
  "cycle_delay": 3600,
  "airtable": {
    "api_key": "patXXXXXXXXXX",
    "base_id": "appXXXXXXXXXX",
    "table_id": "tblXXXXXXXXXX"
  },
  "urls": [
    "https://example.com",
    "https://blog.example.com/post"
  ]
}
```

### Config Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `output_format` | string | `"json"` | `"json"`, `"txt"`, `"md"`, or `"airtable"` |
| `prevent_duplicates` | bool | `true` | Skip already-scraped URLs |
| `worker_mode` | bool | `false` | Enable daemon mode with parallel workers |
| `cycle_delay` | int | `3600` | Seconds between cycles (worker mode) |
| `urls` | array | `[]` | List of URLs or root domains to scrape |

### Airtable Columns

When using Airtable, create these columns in your table:

| Column | Type | Content |
|--------|------|---------|
| URL | Text | Article URL |
| Title | Text | Article title |
| Meta Description | Text | Meta description |
| Category | Text | Article category |
| Content | Long text | HTML content (escaped) |
| JSON | Long text | Full article data |

## Worker Mode

When `worker_mode: true`, the scraper:
1. Groups URLs by domain
2. Creates one worker thread per domain
3. Workers scrape in parallel (don't block each other)
4. After finishing, workers sleep for `cycle_delay` seconds
5. Loop forever until stopped (Ctrl+C)

## CLI Options

| Option | Description |
|--------|-------------|
| `--url`, `-u` | Single URL to scrape |
| `--config`, `-c` | Path to config.json |
| `--sitemap`, `-s` | Enable sitemap mode |
| `--sitemap-url` | Direct sitemap URL |
| `--max`, `-m` | Max articles per sitemap (default: all) |
| `--delay`, `-d` | Delay between requests (default: 1.0s) |
| `--output`, `-o` | Output directory (default: output) |
| `--skip-validation` | Skip URL structure validation |

## Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Project Structure

```
nexobot/
├── nexobot/              # Main package
│   ├── cli.py            # CLI interface
│   ├── config.py         # Configuration
│   ├── extractors.py     # Content extraction
│   ├── models.py         # Data models
│   ├── scraper.py        # Main Scraper class
│   ├── sitemap.py        # Sitemap parsing
│   ├── storage.py        # Output storage
│   ├── validators.py     # URL validation
│   ├── worker.py         # Worker system
│   └── integrations/     # External integrations
│       └── airtable.py   # Airtable client
├── run.py                # Entry point
├── config.json           # Configuration
├── docker-compose.yml    # Docker setup
└── Dockerfile
```

## License

MIT
