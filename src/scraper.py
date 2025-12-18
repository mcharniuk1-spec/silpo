"""HTTP scraper with browser emulation - Production Grade"""

import time
import logging
import requests
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src import config

logger = logging.getLogger(__name__)


class Scraper:
    """Production-grade HTTP scraper with browser emulation"""
    
    # Real browser headers that bypass anti-bot protection
    BROWSER_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7,ru;q=0.6',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Priority': 'u=0, i',
        'Referer': 'https://silpo.ua/',
        'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="131", "Chromium";v="131"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }
    
    def __init__(self):
        """Initialize scraper with session and connection pooling"""
        self.session = requests.Session()
        self.session.headers.update(self.BROWSER_HEADERS)
        
        # Connection pooling for performance
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=Retry(
                total=0,
                connect=0,
                read=0,
                redirect=5,
            )
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.driver = None
        logger.info("✓ Scraper initialized with connection pooling")
    
    def fetch_page(self, url: str, max_attempts: int = 3) -> Optional[str]:
        """
        Fetch page with exponential backoff retries
        
        Args:
            url: URL to fetch
            max_attempts: Maximum number of attempts (default 3)
            
        Returns:
            HTML content or None if failed
        """
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(f"[Attempt {attempt}/{max_attempts}] Fetching: {url}")
                
                response = self.session.get(
                    url,
                    timeout=15,
                    allow_redirects=True
                )
                
                # Log response details for debugging
                logger.debug(f"  Status: {response.status_code}")
                logger.debug(f"  Content-Type: {response.headers.get('Content-Type', 'unknown')}")
                logger.debug(f"  Size: {len(response.text)} chars")
                
                # Handle specific status codes
                if response.status_code == 404:
                    raise Exception(f"HTTP 404 - Page not found")
                elif response.status_code == 403:
                    raise Exception(f"HTTP 403 - Access forbidden (site may be blocking us)")
                elif response.status_code == 429:
                    raise Exception(f"HTTP 429 - Rate limited (too many requests)")
                elif response.status_code >= 400:
                    raise Exception(f"HTTP {response.status_code}")
                
                # Validate response content
                if not response.text or len(response.text) < 1000:
                    raise Exception(f"Empty/short response ({len(response.text)} chars)")
                
                # Verify it's HTML (not error page)
                if 'DOCTYPE' not in response.text[:500] and '<html' not in response.text[:500]:
                    raise Exception("Response doesn't contain valid HTML")
                
                logger.info(f"✓ Successfully fetched {len(response.text)} chars")
                return response.text
                
            except requests.exceptions.Timeout:
                last_error = "Request timeout (15s exceeded)"
                logger.warning(f"  Timeout on attempt {attempt}")
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {str(e)}"
                logger.warning(f"  Connection error on attempt {attempt}")
            except Exception as error:
                last_error = str(error)
                logger.warning(f"  Attempt {attempt} failed: {str(error)}")
            
            # Exponential backoff: 2s, 4s, 6s, etc.
            if attempt < max_attempts:
                delay = config.RETRY_DELAY * attempt
                logger.info(f"  Waiting {delay}s before retry...")
                time.sleep(delay)
        
        logger.error(f"✗ Failed after {max_attempts} attempts: {last_error}")
        return None
    
    def fetch_page_selenium(self, url: str) -> Optional[str]:
        """
        Fetch page using Selenium for JavaScript rendering
        Falls back to requests if Selenium not available
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None if failed
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            logger.info("🎬 Using Selenium for JavaScript rendering...")
            
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument(f'user-agent={self.BROWSER_HEADERS["User-Agent"]}')
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            
            # Wait for products to load
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements('tag name', 'h3')) > 0 or 
                          len(d.find_elements('class name', 'product')) > 0
            )
            
            html = driver.page_source
            driver.quit()
            
            logger.info(f"✓ Selenium fetched {len(html)} chars")
            return html
            
        except ImportError:
            logger.warning("⚠ Selenium not installed, falling back to requests")
            return self.fetch_page(url)
        except Exception as e:
            logger.warning(f"⚠ Selenium failed: {str(e)}, falling back to requests")
            return self.fetch_page(url)
    
    def close(self):
        """Close session and driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.session.close()
        logger.info("✓ Scraper session closed")
