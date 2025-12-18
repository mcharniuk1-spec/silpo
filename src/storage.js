// storage.js - CSV and log file management

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const LOGS_DIR = path.join(__dirname, '..', 'logs');

const DATA_FILE = path.join(DATA_DIR, 'silpo_raw.csv');
const LOG_FILE = path.join(LOGS_DIR, 'silpo_log.csv');

/**
 * Ensure directories and files exist
 */
function ensureLogFiles() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
  
  if (!fs.existsSync(LOGS_DIR)) {
    fs.mkdirSync(LOGS_DIR, { recursive: true });
  }
  
  // Create headers if files don't exist
  if (!fs.existsSync(DATA_FILE)) {
    const header = [
      'upload_ts', 'page_url', 'page_number', 'source', 'product_title', 'brand', 'product_type',
      'fat_pct', 'pack_qty', 'pack_unit', 'price_current', 'price_old', 'discount_pct',
      'price_per_l_or_kg_or_piece', 'rating', 'price_type'
    ];
    fs.writeFileSync(DATA_FILE, header.join(',') + '\n', 'utf-8');
  }
  
  if (!fs.existsSync(LOG_FILE)) {
    const header = ['ts', 'step', 'stage', 'message', 'url', 'status'];
    fs.writeFileSync(LOG_FILE, header.join(',') + '\n', 'utf-8');
  }
}

/**
 * Save products to CSV
 */
function saveToCSV(products) {
  if (!products || products.length === 0) {
    console.log('No products to save');
    return;
  }
  
  const rows = products.map(p => [
    p.upload_ts,
    p.page_url,
    p.page_number,
    p.source,
    escapeCSV(p.product_title),
    p.brand,
    p.product_type,
    p.fat_pct,
    p.pack_qty,
    p.pack_unit,
    p.price_current,
    p.price_old,
    p.discount_pct,
    p.price_per_l_or_kg_or_piece,
    p.rating,
    p.price_type,
  ]);
  
  // Append to file
  for (const row of rows) {
    fs.appendFileSync(DATA_FILE, row.join(',') + '\n', 'utf-8');
  }
  
  console.log(`Appended ${products.length} products to ${DATA_FILE}`);
}

/**
 * Append log entry
 */
function appendLog(logEntry) {
  const row = [
    logEntry.ts,
    logEntry.step,
    logEntry.stage,
    escapeCSV(logEntry.message),
    escapeCSV(logEntry.url),
    logEntry.status,
  ];
  
  fs.appendFileSync(LOG_FILE, row.join(',') + '\n', 'utf-8');
}

/**
 * Escape CSV values
 */
function escapeCSV(value) {
  if (!value) return '';
  const str = String(value);
  
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  
  return str;
}

/**
 * Get recent data
 */
function getRecentData(days = 1) {
  if (!fs.existsSync(DATA_FILE)) return [];
  
  const cutoffTime = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
  const lines = fs.readFileSync(DATA_FILE, 'utf-8').split('\n');
  
  return lines
    .slice(1) // Skip header
    .filter(line => line.trim())
    .filter(line => {
      const ts = line.split(',')[0];
      return ts > cutoffTime;
    });
}

/**
 * Get statistics
 */
function getStatistics() {
  if (!fs.existsSync(DATA_FILE)) return null;
  
  const content = fs.readFileSync(DATA_FILE, 'utf-8');
  const lines = content.split('\n').filter(l => l.trim());
  
  return {
    totalRows: Math.max(0, lines.length - 1), // -1 for header
    lastUpdated: fs.statSync(DATA_FILE).mtime,
    fileSizeKB: fs.statSync(DATA_FILE).size / 1024,
  };
}

module.exports = {
  saveToCSV,
  appendLog,
  ensureLogFiles,
  getRecentData,
  getStatistics,
  DATA_FILE,
  LOG_FILE,
};
