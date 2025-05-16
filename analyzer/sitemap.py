# analyzer/sitemap.py
import logging
from urllib.parse import urljoin, urlparse
import aiohttp
import xml.etree.ElementTree as ET
from typing import Set, List, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__) # Module-specific logger

async def _fetch_robots_txt_content(domain_url: str, session: aiohttp.ClientSession) -> Optional[str]:
    """Fetches the content of robots.txt."""
    robots_url = urljoin(domain_url, "/robots.txt")
    try:
        async with session.get(robots_url, timeout=10) as response:
            if response.status == 200:
                logger.info(f"Successfully fetched robots.txt from {robots_url}")
                return await response.text()
            else:
                logger.info(f"robots.txt not found or not accessible at {robots_url} (Status: {response.status})")
                return None
    except Exception as e:
        logger.error(f"Error fetching robots.txt from {robots_url}: {e}")
        return None

def _extract_sitemap_urls_from_robots_content(robots_content: Optional[str]) -> List[str]:
    """Extracts sitemap URLs from robots.txt content."""
    if not robots_content:
        return []
    return [
        line.split(":", 1)[1].strip()
        for line in robots_content.splitlines()
        if line.lower().startswith("sitemap:")
    ]

async def _parse_sitemap_xml_content(content: str, sitemap_url_source: str) -> Tuple[List[str], List[str]]:
    """
    Parses the XML content of a sitemap.
    Returns a tuple: (list of page URLs, list of child sitemap URLs).
    """
    page_urls: List[str] = []
    child_sitemap_urls: List[str] = []
    try:
        clean_content = content.strip()
        if not clean_content:
            logger.warning(f"Sitemap content is empty for {sitemap_url_source}")
            return page_urls, child_sitemap_urls

        root = ET.fromstring(clean_content)
        namespace = root.tag.split('}')[0] + '}' if '}' in root.tag else ''

        if "sitemapindex" in root.tag.lower():
            for sitemap_node in root.findall(f".//{namespace}sitemap"):
                loc_elem = sitemap_node.find(f"{namespace}loc")
                if loc_elem is not None and loc_elem.text:
                    child_sitemap_urls.append(loc_elem.text.strip())
        elif "urlset" in root.tag.lower():
            for url_elem in root.findall(f".//{namespace}url"):
                loc_elem = url_elem.find(f"{namespace}loc")
                if loc_elem is not None and loc_elem.text:
                    page_urls.append(loc_elem.text.strip())
        else:
            logger.warning(f"Unknown root tag '{root.tag}' or malformed sitemap at {sitemap_url_source}. Attempting to find <loc> tags directly.")
            for loc_elem in root.findall(f".//{namespace}loc"):
                if loc_elem is not None and loc_elem.text:
                    url_text = loc_elem.text.strip()
                    if url_text.lower().endswith(".xml"):
                        child_sitemap_urls.append(url_text)
                    else:
                        page_urls.append(url_text)
        return page_urls, child_sitemap_urls
    except ET.ParseError as e:
        logger.error(f"XML parsing error in sitemap {sitemap_url_source}: {e}. Content: {content[:500]}...")
        return [], []
    except Exception as e:
        logger.error(f"Unexpected error parsing sitemap content from {sitemap_url_source}: {e}")
        return [], []

async def _fetch_and_parse_single_sitemap(
    sitemap_url: str,
    session: aiohttp.ClientSession,
    visited_sitemaps: Set[str],
    semaphore: asyncio.Semaphore  # Added semaphore
) -> Set[str]:
    """
    Fetches and parses a single sitemap URL, recursively handling sitemap indexes.
    `visited_sitemaps` prevents re-fetching and infinite loops.
    Returns a set of page URLs found.
    """
    async with semaphore: # Control concurrency for fetching/parsing sitemaps
        if sitemap_url in visited_sitemaps:
            logger.debug(f"Skipping already visited sitemap: {sitemap_url}")
            return set()
        visited_sitemaps.add(sitemap_url)

        all_page_urls_from_this_branch: Set[str] = set()
        logger.info(f"Fetching sitemap: {sitemap_url}")
        try:
            async with session.get(sitemap_url, timeout=20) as response:
                if response.status == 200:
                    content = await response.text()
                    page_urls, child_sitemap_urls = await _parse_sitemap_xml_content(content, sitemap_url)
                    all_page_urls_from_this_branch.update(page_urls)

                    child_tasks = []
                    for child_s_url_relative in child_sitemap_urls:
                        absolute_child_s_url = urljoin(sitemap_url, child_s_url_relative)
                        if absolute_child_s_url not in visited_sitemaps:
                            # Pass semaphore to recursive calls
                            child_tasks.append(
                                _fetch_and_parse_single_sitemap(absolute_child_s_url, session, visited_sitemaps, semaphore)
                            )
                    
                    if child_tasks:
                        recursive_results = await asyncio.gather(*child_tasks)
                        for recursive_page_urls in recursive_results:
                            all_page_urls_from_this_branch.update(recursive_page_urls)
                else:
                    logger.warning(f"Failed to fetch sitemap {sitemap_url} (Status: {response.status})")
        except aiohttp.ClientError as e:
            logger.error(f"Client error fetching sitemap {sitemap_url}: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching sitemap {sitemap_url}")
        except Exception as e:
            logger.error(f"Error processing sitemap {sitemap_url}: {e}")
        
        return all_page_urls_from_this_branch

async def discover_sitemap_urls(domain_url: str, session: aiohttp.ClientSession) -> List[str]:
    """
    Discovers sitemap URLs by checking robots.txt and common locations.
    Returns a list of potential sitemap URLs.
    """
    sitemap_urls: List[str] = []
    
    robots_content = await _fetch_robots_txt_content(domain_url, session)
    sitemap_urls.extend(_extract_sitemap_urls_from_robots_content(robots_content))

    common_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap.xml.gz", "/sitemap-index.xml.gz"]
    
    for path in common_paths:
        common_sitemap_url = urljoin(domain_url, path)
        if common_sitemap_url not in sitemap_urls:
            sitemap_urls.append(common_sitemap_url)
            
    if sitemap_urls:
        logger.info(f"Discovered potential sitemap URLs for {domain_url}: {sitemap_urls}")
    else:
        logger.info(f"No sitemap URLs discovered in robots.txt or common locations for {domain_url}.")
        
    return sitemap_urls

async def _check_sitemap_url_head(s_url: str, session: aiohttp.ClientSession) -> Optional[str]:
    """Helper function to perform a HEAD request for a single sitemap URL."""
    try:
        async with session.head(s_url, timeout=5, allow_redirects=True) as resp:
            if resp.status == 200:
                logger.info(f"Sitemap confirmed via HEAD: {s_url}")
                return s_url
            else:
                logger.info(f"Sitemap at {s_url} not found or inaccessible via HEAD (Status: {resp.status}).")
                return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.warning(f"Could not perform HEAD request for sitemap {s_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during HEAD request for {s_url}: {e}")
        return None

async def fetch_all_pages_from_sitemaps(discovered_sitemap_urls: List[str], session: aiohttp.ClientSession) -> Set[str]:
    """
    Fetches all page URLs from a list of discovered sitemap URLs.
    Handles sitemap indexes and avoids re-fetching.
    """
    all_pages_found: Set[str] = set()
    visited_sitemaps_cache: Set[str] = set()

    # Concurrently check sitemap URLs with HEAD requests
    head_check_tasks = [_check_sitemap_url_head(s_url, session) for s_url in discovered_sitemap_urls]
    head_results = await asyncio.gather(*head_check_tasks)
    valid_sitemap_urls_to_fetch = [url for url in head_results if url is not None]

    # Define a semaphore to limit concurrent sitemap actual fetches/parses
    # Adjust the limit (e.g., 5 or 10) based on testing and target politeness
    sitemap_fetch_semaphore = asyncio.Semaphore(10) 

    parsing_tasks = []
    for s_url in valid_sitemap_urls_to_fetch:
        if s_url not in visited_sitemaps_cache:
            # Pass the semaphore to the fetching function
            task = _fetch_and_parse_single_sitemap(s_url, session, visited_sitemaps_cache, sitemap_fetch_semaphore)
            parsing_tasks.append(task)
            
    if parsing_tasks:
        results_from_parsing = await asyncio.gather(*parsing_tasks)
        for page_urls_from_sitemap in results_from_parsing:
            all_pages_found.update(page_urls_from_sitemap)
    
    logger.info(f"Total unique pages collected from all processed sitemaps: {len(all_pages_found)}")
    return all_pages_found