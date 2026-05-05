"""
Web scraper for recipe blog pages.

Strategy:
1. Try to extract structured JSON-LD data first (most recipe sites embed this).
2. Fall back to extracting full visible text for LLM processing.
"""

import json
import re
import logging
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Reasonable timeout for HTTP requests (connect, read)
REQUEST_TIMEOUT = (10, 15)

# User-Agent to avoid being blocked by recipe sites
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class ScrapingError(Exception):
    """Raised when scraping fails or the page is not a valid recipe."""
    pass


def validate_url(url: str) -> str:
    """Validate and normalize a URL."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ScrapingError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")
    if not parsed.netloc:
        raise ScrapingError("Invalid URL: no domain found.")
    return url.strip()


def fetch_page(url: str) -> BeautifulSoup:
    """
    Fetch a page and return a BeautifulSoup object.
    Handles connection errors, timeouts, and non-200 responses.
    """
    url = validate_url(url)
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise ScrapingError(f"Request timed out after {REQUEST_TIMEOUT[1]}s for URL: {url}")
    except requests.exceptions.ConnectionError:
        raise ScrapingError(f"Could not connect to URL: {url}. Check the URL and try again.")
    except requests.exceptions.HTTPError as e:
        raise ScrapingError(f"HTTP error {e.response.status_code} for URL: {url}")
    except requests.exceptions.RequestException as e:
        raise ScrapingError(f"Failed to fetch URL: {url}. Error: {str(e)}")

    return BeautifulSoup(response.content, "lxml")


def extract_json_ld(soup: BeautifulSoup) -> Optional[dict]:
    """
    Try to find JSON-LD structured data with @type Recipe.
    Many modern recipe sites include this for SEO/search engines.
    Returns the recipe JSON object or None if not found.
    """
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        # Handle both direct objects and @graph arrays
        candidates = []
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            if "@graph" in data:
                candidates = data["@graph"]
            else:
                candidates = [data]

        for item in candidates:
            if isinstance(item, dict):
                item_type = item.get("@type", "")
                # @type can be a string or list
                if isinstance(item_type, list):
                    if "Recipe" in item_type:
                        return item
                elif item_type == "Recipe":
                    return item
    return None


def extract_visible_text(soup: BeautifulSoup) -> str:
    """
    Extract all visible text from the page body, removing scripts/styles.
    Used as fallback when JSON-LD is not available.
    """
    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    body = soup.find("body")
    if not body:
        return soup.get_text(separator="\n", strip=True)

    text = body.get_text(separator="\n", strip=True)

    # Clean up excessive whitespace and blank lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    # Truncate extremely long text to avoid LLM token limits
    max_chars = 15000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[Content truncated...]"

    return text


def scrape_recipe_page(url: str) -> dict:
    """
    Main scraping function. Returns a dict with:
    - 'json_ld': structured recipe data if found (dict or None)
    - 'text': visible page text (always included as context)
    - 'url': the original URL
    """
    logger.info(f"Scraping recipe from: {url}")
    soup = fetch_page(url)

    # Try structured data first
    json_ld = extract_json_ld(soup)
    if json_ld:
        logger.info("Found JSON-LD recipe data — using structured extraction path.")
    else:
        logger.info("No JSON-LD found — falling back to full-text extraction.")

    # Always extract text as supplementary context
    text = extract_visible_text(soup)

    if not text and not json_ld:
        raise ScrapingError(
            "Could not extract any meaningful content from this page. "
            "It may not be a recipe page, or the content may be loaded dynamically."
        )

    return {
        "json_ld": json_ld,
        "text": text,
        "url": url,
    }
