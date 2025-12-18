"""Main scraper orchestration - Production Grade"""

import sys
import logging
import time
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from src import config
from src.scraper import Scraper
from src.parser import Parser
from src.storage import Storage

logger = logging.getLogger(__name__)


class SilpoScraper:
    """Production-grade Silpo scraper orchestrator"""
    
    def __init__(self):
        """Initialize scraper"""
        self.scraper = Scraper()
        self.start_time = time.time()
        self.batch_stamp = datetime.utcnow().isoformat()
        self.stats = {
            'total_products': 0,
            'pages_success': 0,
            'pages_failed': 0,
            'pages_processed': 0,
            'elapsed_time': 0
        }
    
    def run(self):
        """Main scraper execution workflow"""
        logger.info('=' * 80)
        logger.info('🚀 STARTING SILPO SCRAPER - PRODUCTION GRADE')
        logger.info(f'Batch: {self.batch_stamp}')
        logger.info(f'Max pages: {config.MAX_PAGES}')
        logger.info('=' * 80)
        
        # Ensure output directories exist
        Storage.ensure_directories()
        
        try:
            # Step 1: Test connectivity
            logger.info('Step 1: Testing connectivity to Silpo.ua...')
            if not self.test_connectivity():
                raise Exception("Cannot reach Silpo.ua - website may be blocked or down")
            logger.info('✓ Connectivity OK')
            
            # Step 2: Find last page
            logger.info('Step 2: Finding last page from pagination...')
            max_page = self.find_last_page()
            logger.info(f'✓ Found {max_page} pages (max limit: {config.MAX_PAGES})')
            
            # Step 3: Generate page URLs
            logger.info('Step 3: Generating page URLs...')
            page_urls = self.generate_page_urls(max_page)
            logger.info(f'✓ Generated {len(page_urls)} URLs')
            
            # Step 4: Scrape pages
            logger.info('Step 4: Scraping pages...')
            all_products = []
            
            for i, url in enumerate(page_urls):
                page_num = i + 1
                self.stats['pages_processed'] = page_num
                
                try:
                    logger.info(f'Page {page_num}/{len(page_urls)}: {url}')
                    
                    # Fetch page with fallback to Selenium on first page
                    if i == 0:
                        html = self.scraper.fetch_page_selenium(url)
                    else:
                        html = self.scraper.fetch_page(url, config.RETRY_ATTEMPTS)
                    
                    if not html:
                        raise Exception("Failed to fetch HTML")
                    
                    # Parse products
                    products = Parser.extract_products(html, url, self.batch_stamp, page_num)
                    
                    if products:
                        all_products.extend(products)
                        self.stats['pages_success'] += 1
                        logger.info(f'  ✓ {len(products)} products found')
                        
                        # Show sample products
                        for j, prod in enumerate(products[:3]):
                            title_short = prod['product_title'][:50]
                            logger.info(f'    [{j+1}] {title_short} | {prod["price_current"]}₴ | {prod["pack_qty"]}{prod["pack_unit"]}')
                        
                        if len(products) > 3:
                            logger.info(f'    ... and {len(products) - 3} more')
                    else:
                        logger.warning(f'  ✗ No products extracted')
                    
                    # Log to file
                    Storage.append_log({
                        'ts': datetime.utcnow().isoformat(),
                        'step': 'PARSE',
                        'stage': f'page_{page_num}/{len(page_urls)}',
                        'message': f'Extracted {len(products)} products',
                        'url': url,
                        'status': 'success',
                    })
                    
                    # Delay before next request (respectful scraping)
                    if i < len(page_urls) - 1:
                        delay = config.REQUEST_DELAY
                        logger.debug(f'  Waiting {delay}s before next request...')
                        time.sleep(delay)
                    
                except Exception as error:
                    self.stats['pages_failed'] += 1
                    logger.error(f'  ✗ Failed: {str(error)}')
                    
                    Storage.append_log({
                        'ts': datetime.utcnow().isoformat(),
                        'step': 'ERROR',
                        'stage': f'page_{page_num}',
                        'message': str(error),
                        'url': url,
                        'status': 'failed',
                    })
            
            # Step 5: Save results
            logger.info('Step 5: Saving results...')
            
            if all_products:
                Storage.save_products(all_products)
                self.stats['total_products'] = len(all_products)
                logger.info(f'✓ Saved {len(all_products)} products to {config.DATA_FILE}')
                
                Storage.append_log({
                    'ts': datetime.utcnow().isoformat(),
                    'step': 'WRITE',
                    'stage': 'save_csv',
                    'message': f'Written {len(all_products)} products',
                    'url': 'N/A',
                    'status': 'success',
                })
            else:
                logger.warning('⚠ No products to save')
            
            # Step 6: Print summary
            self.stats['elapsed_time'] = time.time() - self.start_time
            
            logger.info('=' * 80)
            logger.info('✅ SCRAPER COMPLETED SUCCESSFULLY')
            logger.info(f"  📊 Total products: {self.stats['total_products']}")
            logger.info(f"  ✓ Pages success: {self.stats['pages_success']}")
            logger.info(f"  ✗ Pages failed: {self.stats['pages_failed']}")
            logger.info(f"  ⏱ Elapsed time: {self.stats['elapsed_time']:.2f}s")
            logger.info('=' * 80)
            
            # Log final stats
            Storage.append_log({
                'ts': datetime.utcnow().isoformat(),
                'step': 'DONE',
                'stage': 'run_scraper',
                'message': json.dumps(self.stats),
                'url': 'N/A',
                'status': 'success',
            })
        
        except Exception as error:
            logger.error(f'🔴 CRITICAL ERROR: {str(error)}', exc_info=True)
            self.stats['elapsed_time'] = time.time() - self.start_time
            
            Storage.append_log({
                'ts': datetime.utcnow().isoformat(),
                'step': 'CRITICAL_ERROR',
                'stage': 'run_scraper',
                'message': str(error),
                'url': 'N/A',
                'status': 'failed',
            })
            
            sys.exit(1)
        
        finally:
            self.scraper.close()
    
    def test_connectivity(self) -> bool:
        """Test if we can reach Silpo.ua"""
        try:
            html = self.scraper.fetch_page(config.BASE_URL, max_attempts=2)
            return html is not None and len(html) > 500
        except Exception as e:
            logger.error(f"Connectivity test failed: {str(e)}")
            return False
    
    def find_last_page(self) -> int:
        """Find last page number from pagination"""
        try:
            html = self.scraper.fetch_page(config.BASE_URL, config.RETRY_ATTEMPTS)
            if not html:
                logger.warning("Could not fetch first page for pagination detection")
                return min(10, config.MAX_PAGES)
            
            # Method 1: Direct URL parameters in href
            page_matches = re.findall(r'[?&]page=(\d+)', html)
            if page_matches:
                max_page = max(int(p) for p in page_matches)
                if max_page <= config.MAX_PAGES:
                    logger.info(f"  Found pagination via URL params: {max_page} pages")
                    return max_page
            
            # Method 2: Link text with page numbers
            link_matches = re.findall(
                r'<a[^>]*href="[^"]*page=(\d+)[^"]*"[^>]*>.*?(\d+).*?</a>',
                html,
                re.DOTALL
            )
            if link_matches:
                page_nums = [int(m[0]) for m in link_matches]
                max_page = max(page_nums) if page_nums else 1
                if max_page <= config.MAX_PAGES:
                    logger.info(f"  Found pagination via link text: {max_page} pages")
                    return min(max_page, config.MAX_PAGES)
            
            # Method 3: Look for pagination markers
            if 'page=' in html:
                logger.info("  Found pagination markers")
                return min(10, config.MAX_PAGES)
            
            logger.warning("  No pagination detected, using default")
            return 1
        
        except Exception as error:
            logger.error(f'Failed to find last page: {str(error)}')
            return min(5, config.MAX_PAGES)
    
    def generate_page_urls(self, max_page: int) -> List[str]:
        """Generate list of page URLs"""
        urls = []
        
        for p in range(1, max_page + 1):
            if p == 1:
                # First page has no query parameter
                urls.append(config.BASE_URL)
            else:
                # Pages 2+ use ?page=N
                urls.append(f'{config.BASE_URL}?page={p}')
        
        return urls


def main():
    """Entry point for scraper"""
    scraper = SilpoScraper()
    scraper.run()


if __name__ == '__main__':
    main()
