"""Advanced HTML parsing - Production Grade"""

import re
import logging
from typing import List, Dict, Optional

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    BeautifulSoup = None

from src import config

logger = logging.getLogger(__name__)


class Parser:
    """Production-grade HTML parser for Silpo products"""
    
    @staticmethod
    def extract_products(
        html: str,
        page_url: str,
        batch_stamp: str,
        page_number: int
    ) -> List[Dict]:
        """
        Extract all products from HTML with multiple strategies
        
        Args:
            html: HTML content
            page_url: Page URL
            batch_stamp: Batch ISO timestamp
            page_number: Page number
            
        Returns:
            List of product dictionaries
        """
        products = []
        
        if not html or len(html) < 1000:
            logger.warning("HTML too short to parse")
            return products
        
        # Strategy 1: BeautifulSoup (most reliable)
        if HAS_BS4:
            try:
                soup = BeautifulSoup(html, 'html.parser')
                products = Parser._extract_with_beautifulsoup(
                    soup, page_url, batch_stamp, page_number
                )
                if products:
                    logger.info(f"✓ BeautifulSoup found {len(products)} products")
                    return products
            except Exception as e:
                logger.warning(f"BeautifulSoup strategy failed: {str(e)}")
        
        # Strategy 2: Regex-based extraction (fallback)
        try:
            products = Parser._extract_with_regex(
                html, page_url, batch_stamp, page_number
            )
            if products:
                logger.info(f"✓ Regex strategy found {len(products)} products")
                return products
        except Exception as e:
            logger.warning(f"Regex strategy failed: {str(e)}")
        
        logger.warning("⚠ No products extracted using any strategy")
        return []
    
    @staticmethod
    def _extract_with_beautifulsoup(
        soup,
        page_url: str,
        batch_stamp: str,
        page_number: int
    ) -> List[Dict]:
        """Extract using BeautifulSoup with multiple selectors"""
        products = []
        
        # Try multiple selectors in order of preference
        selectors = [
            'h3',                      # Original - products wrapped in h3
            '[class*="product"]',      # Product divs
            '[class*="item"]',         # Item cards
            'a[href*="/product/"]',    # Product links
            'div.product',             # Standard product div
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if len(elements) > 3:
                    logger.debug(f"Using selector: {selector} ({len(elements)} elements)")
                    
                    for element in elements:
                        product = Parser._parse_element(
                            element, page_url, batch_stamp, page_number
                        )
                        if product:
                            products.append(product)
                    
                    if products:
                        return products
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {str(e)}")
                continue
        
        return products
    
    @staticmethod
    def _extract_with_regex(
        html: str,
        page_url: str,
        batch_stamp: str,
        page_number: int
    ) -> List[Dict]:
        """Extract using regex patterns (fallback)"""
        products = []
        
        # Find price patterns: "Title ... Price грн"
        price_pattern = r'([\w\s\-\.А-Яа-яЁёІіЇїЄєҐґ\'ʼ'`]{5,200}?)\s*(\d{1,4}(?:[.,]\d{2})?)\s*(?:грн|₴)'
        
        seen_titles = set()
        
        for match in re.finditer(price_pattern, html):
            try:
                title_raw = match.group(1)
                price_str = match.group(2)
                
                # Clean and validate title
                title = Parser._clean_text(title_raw)
                if not title or len(title) < 5 or len(title) > 200:
                    continue
                
                # Avoid duplicates
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                
                # Extract and validate price
                price = Parser._to_num(price_str)
                if price < 5 or price > 2000:
                    continue
                
                # Extract other attributes
                brand = Parser._extract_brand(title)
                product_type = Parser._extract_product_type(title)
                fat = Parser._extract_fat(title)
                pack = Parser._extract_pack(title)
                
                products.append({
                    'upload_ts': batch_stamp,
                    'page_url': page_url,
                    'page_number': page_number,
                    'source': 'https://silpo.ua',
                    'product_title': title,
                    'brand': brand,
                    'product_type': product_type,
                    'fat_pct': fat,
                    'pack_qty': pack['qty'],
                    'pack_unit': pack['unit'],
                    'price_current': price,
                    'price_old': '',
                    'discount_pct': '',
                    'price_per_l_or_kg_or_piece': Parser._calculate_price_per_unit(price, pack),
                    'rating': '',
                    'price_type': 'regular',
                })
            except Exception as e:
                logger.debug(f"Regex parse error: {str(e)}")
                continue
        
        return products
    
    @staticmethod
    def _parse_element(element, page_url: str, batch_stamp: str, page_number: int) -> Optional[Dict]:
        """Parse individual element"""
        try:
            text = element.get_text()
            title = Parser._extract_title(text)
            
            if not title or len(title) < 5:
                return None
            
            # Extract prices from element and surrounding context
            full_text = text + ' ' + (element.parent.get_text() if element.parent else '')
            price_info = Parser._extract_prices(full_text)
            
            if not price_info or not price_info.get('current'):
                return None
            
            # Extract other attributes
            brand = Parser._extract_brand(title)
            product_type = Parser._extract_product_type(title)
            fat = Parser._extract_fat(title)
            pack = Parser._extract_pack(title)
            rating = Parser._extract_rating(full_text)
            
            return {
                'upload_ts': batch_stamp,
                'page_url': page_url,
                'page_number': page_number,
                'source': 'https://silpo.ua',
                'product_title': title,
                'brand': brand,
                'product_type': product_type,
                'fat_pct': fat,
                'pack_qty': pack['qty'],
                'pack_unit': pack['unit'],
                'price_current': price_info['current'],
                'price_old': price_info.get('old', ''),
                'discount_pct': price_info.get('discount', ''),
                'price_per_l_or_kg_or_piece': Parser._calculate_price_per_unit(price_info['current'], pack),
                'rating': rating,
                'price_type': price_info.get('type', 'regular'),
            }
        except Exception as e:
            logger.debug(f"Element parse error: {str(e)}")
            return None
    
    @staticmethod
    def _extract_title(text: str) -> str:
        """Extract and clean product title"""
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')).strip()
        
        # Remove prices
        without_price = re.sub(r'\d{1,4}(?:[.,]\d{2})?\s*(?:грн|₴)', '', cleaned).strip()
        
        # Limit length
        title = without_price[:200].strip()
        
        # Validate
        if not title or len(title) < 3:
            return None
        
        return title
    
    @staticmethod
    def _extract_prices(text: str) -> Optional[Dict]:
        """Extract price information"""
        price_regex = r'(\d{2,4}(?:[.,]\d{2})?)\s*(?:грн|₴)'
        prices = []
        
        for match in re.finditer(price_regex, text):
            price = Parser._to_num(match.group(1))
            if 5 < price < 2000:
                prices.append(price)
        
        if not prices:
            return None
        
        current = prices[0]
        old = ''
        discount = ''
        price_type = 'regular'
        
        # Check for discount (old price usually higher than current)
        discount_match = re.search(r'-\s*(\d{1,2})%', text)
        if discount_match and len(prices) >= 2:
            discount = discount_match.group(1)
            price_type = 'discount'
            old = prices[1]
        
        return {
            'current': current,
            'old': old,
            'discount': discount,
            'type': price_type,
        }
    
    @staticmethod
    def _extract_brand(title: str) -> str:
        """Extract brand name from title"""
        # Check for brands in guillemets («...»)
        match = re.search(r'«([^»]{2,30})»', title)
        if match:
            return match.group(1)
        
        # Check known brands list
        title_lower = title.lower()
        for brand in config.KNOWN_BRANDS:
            if brand.lower() in title_lower:
                return brand
        
        # Extract first capitalized word as brand
        match = re.match(r'^([A-ZА-ЯЁІЇЄҐ][\wА-Яа-яЁёІіЇїЄєҐґ\-\'ʼ'`]{1,25})', title)
        if match:
            brand = match.group(1).strip()
            
            # Exclude common non-brand words
            exclude = ['Молоко', 'Вершки', 'Кефір', 'Сметана', 'Йогурт', 'Масло', 'Маргарин']
            if brand not in exclude and len(brand) > 2:
                return brand
        
        return ''
    
    @staticmethod
    def _extract_product_type(title: str) -> str:
        """Extract product type category"""
        title_lower = title.lower()
        
        for ptype, keywords in config.PRODUCT_TYPES.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return ptype
        
        return ''
    
    @staticmethod
    def _extract_fat(title: str) -> str:
        """Extract fat percentage"""
        patterns = [
            r'([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'жир[^0-9]*([0-9]+(?:[.,][0-9]+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                fat = match.group(1).replace(',', '.')
                try:
                    fat_num = float(fat)
                    if 0 <= fat_num <= 50:
                        return fat
                except:
                    pass
        
        return ''
    
    @staticmethod
    def _extract_pack(title: str) -> Dict:
        """Extract package information"""
        patterns = [
            {'regex': r'([0-9]+(?:[.,][0-9]+)?)\s*л\b', 'unit': 'мл', 'multiply': 1000},
            {'regex': r'([0-9]{2,4})\s*мл\b', 'unit': 'мл', 'multiply': 1},
            {'regex': r'([0-9]{2,4})\s*г\b', 'unit': 'г', 'multiply': 1},
            {'regex': r'([0-9]{1,3})\s*шт', 'unit': 'шт', 'multiply': 1},
            {'regex': r'([0-9]+(?:[.,][0-9]+)?)\s*кг', 'unit': 'г', 'multiply': 1000},
        ]
        
        for pattern in patterns:
            match = re.search(pattern['regex'], title, re.IGNORECASE)
            if match:
                qty = int(round(Parser._to_num(match.group(1)) * pattern['multiply']))
                return {'qty': qty if qty > 0 else '', 'unit': pattern['unit']}
        
        return {'qty': '', 'unit': ''}
    
    @staticmethod
    def _extract_rating(text: str) -> str:
        """Extract product rating"""
        patterns = [
            r'★\s*([1-5](?:[.,][0-9])?)',
            r'⭐\s*([1-5](?:[.,][0-9])?)',
            r'([1-5](?:[.,][0-9])?)\s*(?:★|⭐)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    rating = Parser._to_num(match.group(1))
                    if 1 <= rating <= 5:
                        return rating
                except:
                    pass
        
        return ''
    
    @staticmethod
    def _calculate_price_per_unit(price: float, pack: Dict) -> float:
        """Calculate price per unit (UAH/L, UAH/kg, or UAH/piece)"""
        if not price or not pack['qty']:
            return ''
        
        try:
            if pack['unit'] == 'шт':
                # Price per piece
                return round((price / pack['qty']) * 100) / 100
            else:
                # Price per liter or kilogram
                base_qty = pack['qty'] / 1000
                if base_qty <= 0:
                    return ''
                return round((price / base_qty) * 100) / 100
        except:
            return ''
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize text"""
        return re.sub(r'\s+', ' ', text.replace('\n', ' ').replace('\r', ' ')).strip()
    
    @staticmethod
    def _to_num(s: str) -> float:
        """Convert string to float number"""
        try:
            return float(str(s).replace(',', '.'))
        except:
            return 0
