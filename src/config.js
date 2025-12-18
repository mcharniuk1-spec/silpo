// config.js - Configuration for Silpo scraper

module.exports = {
  // Base URL for category
  BASE_URL: 'https://silpo.ua/category/molochni-produkty-ta-iaitsia-234',
  
  // Max pages to scrape (limit to 10 for initial run)
  MAX_PAGES: 10,
  
  // Request settings
  REQUEST_DELAY: 1500, // ms between requests
  RETRY_DELAY: 2000, // ms initial delay for retries
  RETRY_ATTEMPTS: 3,
  
  // User Agent
  USER_AGENT: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  
  // Known brands for Ukrainian dairy market
  knownBrands: [
    'Яготинське', 'Ферма', 'Галичина', 'Селянське', 'ПростоНаше', 'Премія',
    'Молокія', 'Lactel', 'Бурьонка', 'На здоров\'я', 'Даніссімо', 'Активіа',
    'Простоквашино', 'Чудо', 'Агуня', 'Растішка', 'Ростишка', 'Actimel',
    'Danone', 'Muller', 'Біло', 'Білоцерківське', 'Тульчинка', 'Марійка',
    'Злагода', 'President', 'Деліссімо', 'Alpro', 'Valio', 'Elle&Vire'
  ],
  
  // Product types in dairy category
  productTypes: {
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
    'каша': ['каша', 'хлопья']
  },
  
  // CSV column headers
  csvHeaders: [
    'upload_ts',
    'page_url',
    'page_number',
    'source',
    'product_title',
    'brand',
    'product_type',
    'fat_pct',
    'pack_qty',
    'pack_unit',
    'price_current',
    'price_old',
    'discount_pct',
    'price_per_l_or_kg_or_piece',
    'rating',
    'price_type'
  ],
};
