"""Configuration for Silpo scraper - Production Grade"""

import os
from pathlib import Path

# ============================================================================
# DIRECTORIES
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# ============================================================================
# URLS
# ============================================================================

BASE_URL = "https://silpo.ua/category/molochni-produkty-ta-iaitsia-234"

# ============================================================================
# SCRAPING SETTINGS
# ============================================================================

MAX_PAGES = 10                  # Maximum pages to scrape (increase to 45 for more)
REQUEST_DELAY = 1.5             # Seconds between requests (respectful scraping)
RETRY_DELAY = 2.0              # Seconds for first retry
RETRY_ATTEMPTS = 3             # Total attempts per URL

# ============================================================================
# BROWSER HEADERS (for Silpo.ua anti-bot protection)
# ============================================================================

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# ============================================================================
# KNOWN BRANDS - Ukrainian Dairy Market
# ============================================================================

KNOWN_BRANDS = [
    # Local Ukrainian brands
    'Яготинське',
    'Ферма',
    'Галичина',
    'Селянське',
    'ПростоНаше',
    'Премія',
    'Молокія',
    'Бурьонка',
    'На здоров\'я',
    'Даніссімо',
    'Активіа',
    'Простоквашино',
    'Чудо',
    'Агуня',
    'Растішка',
    'Ростишка',
    
    # International brands
    'Lactel',
    'Actimel',
    'Danone',
    'Muller',
    'Alpro',
    'Valio',
    'Elle&Vire',
    'President',
    'Деліссімо',
    
    # Local premium brands
    'Біло',
    'Білоцерківське',
    'Тульчинка',
    'Марійка',
    'Злагода',
]

# ============================================================================
# PRODUCT TYPES - Dairy Category Classification
# ============================================================================

PRODUCT_TYPES = {
    'молоко': ['молоко'],
    'вершки': ['вершки'],
    'сир': ['сир '],
    'сметана': ['сметана'],
    'йогурт': ['йогурт'],
    'кефір': ['кефір'],
    'ряжанка': ['ряжанка'],
    'масло': ['масло'],
    'маргарин': ['маргарин'],
    'яйця': ['яйце', 'яйця'],
    'сирок': ['сирок'],
    'десерт': ['десерт'],
    'творог': ['творог', 'кисломолочний'],
    'згущене': ['згущене'],
    'каша': ['каша', 'хлопья'],
}

# ============================================================================
# CSV SCHEMA - Data Output Format
# ============================================================================

CSV_HEADERS = [
    'upload_ts',                    # ISO timestamp of upload
    'page_url',                     # Source page URL
    'page_number',                  # Page number in pagination
    'source',                       # Source website
    'product_title',                # Product name/title
    'brand',                        # Brand name
    'product_type',                 # Category (молоко, йогурт, etc)
    'fat_pct',                      # Fat percentage
    'pack_qty',                     # Package quantity (numeric)
    'pack_unit',                    # Package unit (мл, г, шт)
    'price_current',                # Current price (UAH)
    'price_old',                    # Old price if discount
    'discount_pct',                 # Discount percentage
    'price_per_l_or_kg_or_piece',   # Price per liter/kg/piece
    'rating',                       # Product rating
    'price_type',                   # regular, discount, etc
]

# ============================================================================
# FILE PATHS
# ============================================================================

DATA_FILE = DATA_DIR / "silpo_raw.csv"
LOG_FILE = LOGS_DIR / "silpo_log.csv"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)
logger.info("Config loaded successfully")
