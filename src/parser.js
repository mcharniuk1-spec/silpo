// parser.js - Product parsing logic

const cheerio = require('cheerio');
const config = require('./config');

/**
 * Extract all products from HTML
 */
function extractProducts(html, pageUrl, batchStamp, pageNumber) {
  const $ = cheerio.load(html);
  const products = [];
  
  // Try multiple selectors
  const selectors = [
    'h3', // Original method - products under H3 tags
    '[data-test-id*="product"]',
    '.product',
    '[class*="product"]',
  ];
  
  let productElements = $();
  for (const selector of selectors) {
    productElements = $(selector);
    if (productElements.length > 5) break; // Found reasonable number
  }
  
  productElements.each((index, element) => {
    try {
      const text = $(element).text();
      
      // Extract price from element or nearby siblings
      let priceMatch = text.match(/(\d{2,4}(?:[.,]\d{2})?)\s*(?:грн|₴)/);
      
      if (!priceMatch) {
        // Try to find price in parent or siblings
        const parent = $(element).closest('div, li, article');
        const parentText = parent.text();
        priceMatch = parentText.match(/(\d{2,4}(?:[.,]\d{2})?)\s*(?:грн|₴)/);
      }
      
      if (!priceMatch) return; // Skip if no price
      
      const product = parseProductElement($, element, pageUrl, batchStamp, pageNumber, text);
      if (product) {
        products.push(product);
      }
    } catch (e) {
      console.warn(`Error parsing product element: ${e.message}`);
    }
  });
  
  return products;
}

/**
 * Parse individual product element
 */
function parseProductElement($, element, pageUrl, batchStamp, pageNumber, elementText) {
  const title = extractTitle(elementText);
  
  if (!title || title.length < 5) return null;
  
  // Get all text from element and siblings for price extraction
  const fullText = $(element).text() + ' ' + $(element).parent().text();
  
  // Extract prices
  const priceInfo = extractPrices(fullText);
  if (!priceInfo.current) return null;
  
  // Extract other attributes
  const brand = extractBrand(title);
  const productType = extractProductType(title);
  const fat = extractFat(title);
  const pack = extractPack(title, fullText);
  const rating = extractRating(fullText);
  const pricePerUnit = calculatePricePerUnit(priceInfo.current, pack);
  
  return {
    upload_ts: batchStamp,
    page_url: pageUrl,
    page_number: pageNumber,
    source: 'https://silpo.ua',
    product_title: title,
    brand: brand,
    product_type: productType,
    fat_pct: fat,
    pack_qty: pack.qty,
    pack_unit: pack.unit,
    price_current: priceInfo.current,
    price_old: priceInfo.old || '',
    discount_pct: priceInfo.discount || '',
    price_per_l_or_kg_or_piece: pricePerUnit,
    rating: rating,
    price_type: priceInfo.type,
  };
}

/**
 * Extract product title
 */
function extractTitle(text) {
  const cleaned = text
    .replace(/\s+/g, ' ')
    .replace(/[\r\n\t]/g, ' ')
    .trim();
  
  // Remove price from title
  const withoutPrice = cleaned.replace(/\d{1,4}(?:[.,]\d{2})?\s*(?:грн|₴)/g, '').trim();
  
  // Take first 150 chars as title
  return withoutPrice.substring(0, 150).trim();
}

/**
 * Extract prices
 */
function extractPrices(text) {
  const priceRegex = /(\d{2,4}(?:[.,]\d{2})?)\s*(?:грн|₴)/g;
  const prices = [];
  
  let match;
  while ((match = priceRegex.exec(text)) !== null) {
    const price = toNum(match[1]);
    if (price > 5 && price < 2000) {
      prices.push(price);
    }
  }
  
  if (prices.length === 0) return null;
  
  // Analyze prices
  let current = prices[0];
  let old = '';
  let discount = '';
  let type = 'regular';
  
  // Check for discount pattern
  const discountMatch = text.match(/-\s*(\d{1,2})%/);
  if (discountMatch && prices.length >= 2) {
    discount = discountMatch[1];
    type = 'discount';
    old = prices[1];
  }
  
  return {
    current,
    old: old || '',
    discount: discount || '',
    type,
  };
}

/**
 * Extract brand
 */
function extractBrand(title) {
  // Check for brands in quotes
  const quoteBrand = title.match(/«([^»]{2,30})»/);
  if (quoteBrand) return quoteBrand[1];
  
  // Check known brands
  const titleLower = title.toLowerCase();
  for (const brand of config.knownBrands) {
    if (titleLower.includes(brand.toLowerCase())) {
      return brand;
    }
  }
  
  // Extract first word as brand
  const firstWord = title.match(/^([A-ZА-ЯЁІЇЄҐ][\wА-Яа-яЁёІіЇїЄєҐґ\-\'ʼ'`\s]{1,25}?)(?:\s|$)/);
  if (firstWord) {
    const brand = firstWord[1].trim();
    const excludeWords = ['Молоко', 'Вершки', 'Кефір', 'Сметана', 'Йогурт'];
    if (!excludeWords.includes(brand) && brand.length > 2) {
      return brand;
    }
  }
  
  return '';
}

/**
 * Extract product type
 */
function extractProductType(title) {
  const titleLower = title.toLowerCase();
  
  for (const [type, keywords] of Object.entries(config.productTypes)) {
    for (const keyword of keywords) {
      if (titleLower.includes(keyword)) {
        return type;
      }
    }
  }
  
  return '';
}

/**
 * Extract fat percentage
 */
function extractFat(title) {
  // Pattern: "2.5%" or "жирність 2.5"
  const patterns = [
    /([0-9]+(?:[.,][0-9]+)?)\s*%/,
    /жир\w*\s+([0-9]+(?:[.,][0-9]+)?)/i,
  ];
  
  for (const pattern of patterns) {
    const match = title.match(pattern);
    if (match) {
      const fat = match[1].replace(',', '.');
      const num = parseFloat(fat);
      if (num >= 0 && num <= 50) {
        return fat;
      }
    }
  }
  
  return '';
}

/**
 * Extract package info
 */
function extractPack(title, text) {
  const patterns = [
    { regex: /([0-9]+(?:[.,][0-9]+)?)\s*л\b/i, unit: 'мл', multiply: 1000 },
    { regex: /([0-9]{2,4})\s*мл\b/i, unit: 'мл', multiply: 1 },
    { regex: /([0-9]{2,4})\s*г\b/i, unit: 'г', multiply: 1 },
    { regex: /([0-9]{1,2})\s*шт/i, unit: 'шт', multiply: 1 },
    { regex: /([0-9]{2,4})\s*кг/i, unit: 'г', multiply: 1000 },
  ];
  
  const searchText = title + ' ' + text;
  
  for (const pattern of patterns) {
    const match = searchText.match(pattern.regex);
    if (match) {
      const qty = Math.round(toNum(match[1]) * pattern.multiply);
      return { qty: qty || '', unit: pattern.unit };
    }
  }
  
  return { qty: '', unit: '' };
}

/**
 * Extract rating
 */
function extractRating(text) {
  const patterns = [
    /★\s*([1-5](?:[.,][0-9])?)/,
    /⭐\s*([1-5](?:[.,][0-9])?)/,
    /([1-5](?:[.,][0-9])?)\s*(?:stars?|зір|★|⭐)/i,
  ];
  
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      const rating = toNum(match[1]);
      if (rating >= 1 && rating <= 5) {
        return rating;
      }
    }
  }
  
  return '';
}

/**
 * Calculate price per unit
 */
function calculatePricePerUnit(price, pack) {
  if (!price || !pack.qty) return '';
  
  try {
    if (pack.unit === 'шт') {
      // Price per piece
      return Math.round((price / pack.qty) * 100) / 100;
    } else {
      // Price per kg/l
      const baseQty = pack.qty / 1000;
      if (baseQty <= 0) return '';
      return Math.round((price / baseQty) * 100) / 100;
    }
  } catch (e) {
    return '';
  }
}

/**
 * Convert string to number
 */
function toNum(s) {
  return Number(String(s).replace(',', '.'));
}

module.exports = {
  extractProducts,
  parseProductElement,
  extractTitle,
  extractPrices,
  extractBrand,
  extractProductType,
  extractFat,
  extractPack,
  extractRating,
  calculatePricePerUnit,
};

