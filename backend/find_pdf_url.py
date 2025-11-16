#!/usr/bin/env python3
"""
FRT PDF URL Finder
Helper utility to find the actual PDF download link from the RCMP FRT page
"""

import requests
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}


def find_pdf_links(url):
    """
    Fetch a webpage and find all PDF links

    Args:
        url: URL of the webpage to search

    Returns:
        List of PDF URLs found on the page
    """
    try:
        print(f"Fetching: {url}")
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
        response.raise_for_status()

        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all links
        links = soup.find_all('a', href=True)
        print(f"\nFound {len(links)} total links on page")

        # Filter for PDF links
        pdf_links = []
        for link in links:
            href = link['href']

            # Check if it's a PDF link
            if '.pdf' in href.lower():
                # Convert relative URLs to absolute
                absolute_url = urljoin(url, href)
                pdf_links.append({
                    'url': absolute_url,
                    'text': link.get_text(strip=True),
                    'title': link.get('title', '')
                })

        return pdf_links

    except Exception as e:
        print(f"Error: {e}")
        return []


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Find PDF links on RCMP FRT page')
    parser.add_argument(
        '--url',
        default='https://rcmp.ca/en/firearms/firearms-reference-table',
        help='URL to search for PDF links'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("FRT PDF URL Finder")
    print("=" * 70)
    print()

    # Find PDF links
    pdf_links = find_pdf_links(args.url)

    if pdf_links:
        print(f"\n✓ Found {len(pdf_links)} PDF link(s):\n")

        for i, link in enumerate(pdf_links, 1):
            print(f"{i}. {link['text']}")
            print(f"   URL: {link['url']}")
            if link['title']:
                print(f"   Title: {link['title']}")
            print()

        print("\nTo use a PDF URL with the parser:")
        print(f"  python src/frt_parser.py --url \"{pdf_links[0]['url']}\"")
        print("\nOr set environment variable:")
        print(f"  export FRT_PDF_URL=\"{pdf_links[0]['url']}\"")
        print("  python src/frt_parser.py")

    else:
        print("\n✗ No PDF links found on the page.")
        print("\nPossible reasons:")
        print("  - PDF link is dynamically loaded (JavaScript)")
        print("  - PDF is behind authentication")
        print("  - URL structure has changed")
        print("\nManual steps:")
        print(f"  1. Visit {args.url} in your browser")
        print("  2. Find and click the FRT PDF download link")
        print("  3. Copy the URL from your browser's address bar or download dialog")
        print("  4. Use: python src/frt_parser.py --url \"<pdf-url>\"")
        print("     Or: Manually download and save to backend/data/frt_current.pdf")
        print("         Then: python src/frt_parser.py --skip-download")


if __name__ == '__main__':
    main()
