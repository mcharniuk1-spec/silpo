"""CSV and log file management - Production Grade"""

import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from src import config

logger = logging.getLogger(__name__)


class Storage:
    """CSV file management for scraper data"""
    
    @staticmethod
    def ensure_directories():
        """Ensure data and logs directories exist"""
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Directories ensured: {config.DATA_DIR}, {config.LOGS_DIR}")
        
        # Create headers if files don't exist
        if not config.DATA_FILE.exists():
            Storage.create_data_file()
        
        if not config.LOG_FILE.exists():
            Storage.create_log_file()
    
    @staticmethod
    def create_data_file():
        """Create data CSV with headers"""
        try:
            with open(config.DATA_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=config.CSV_HEADERS)
                writer.writeheader()
            logger.info(f"✓ Created {config.DATA_FILE}")
        except Exception as e:
            logger.error(f"Failed to create data file: {str(e)}")
    
    @staticmethod
    def create_log_file():
        """Create log CSV with headers"""
        headers = ['ts', 'step', 'stage', 'message', 'url', 'status']
        try:
            with open(config.LOG_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
            logger.info(f"✓ Created {config.LOG_FILE}")
        except Exception as e:
            logger.error(f"Failed to create log file: {str(e)}")
    
    @staticmethod
    def save_products(products: List[Dict]):
        """
        Append products to CSV
        
        Args:
            products: List of product dictionaries
        """
        if not products:
            logger.warning("No products to save")
            return
        
        try:
            with open(config.DATA_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=config.CSV_HEADERS)
                writer.writerows(products)
            logger.info(f"✓ Appended {len(products)} products to {config.DATA_FILE}")
        except Exception as e:
            logger.error(f"Failed to save products: {str(e)}")
    
    @staticmethod
    def append_log(log_entry: Dict):
        """
        Append log entry
        
        Args:
            log_entry: Dictionary with ts, step, stage, message, url, status
        """
        headers = ['ts', 'step', 'stage', 'message', 'url', 'status']
        
        try:
            with open(config.LOG_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writerow(log_entry)
        except Exception as e:
            logger.error(f"Failed to append log: {str(e)}")
    
    @staticmethod
    def get_statistics() -> Dict:
        """Get file statistics"""
        if not config.DATA_FILE.exists():
            return None
        
        try:
            with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            return {
                'total_rows': max(0, len(lines) - 1),  # -1 for header
                'last_updated': datetime.fromtimestamp(config.DATA_FILE.stat().st_mtime),
                'file_size_kb': round(config.DATA_FILE.stat().st_size / 1024, 2),
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return None
