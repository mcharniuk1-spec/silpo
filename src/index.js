// index.js - Main scraper entry point

const fs = require('fs');
const path = require('path');
const config = require('./config');
const { fetchPageWithRetry, sleep, logger } = require('./fetcher');
const { extractProducts } = require('./parser');
const { saveToCSV, appendLog, ensureLogFiles } = require('./storage');

/**
 * Main scraper function
 */
async function runSilpoScraper() {
  const startTime = Date.now();
  const batchStamp = new Date().toISOString();
  
  logger.info('='.repeat(80));
  logger.info('STARTING SILPO SCRAPER');
  logger.info(`Batch: ${batchStamp}`);
  logger.info(`Max pages: ${config.MAX_PAGES}`);
  logger.info('='.repeat(80));
  
  // Ensure log files exist
  ensureLogFiles();
  
  try {
    // Step 1: Find last page
    logger.info('Step 1: Finding last page from pagination...');
    const maxPage = await findLastPage();
    logger.info(`Found ${maxPage} pages (max limit: ${config.MAX_PAGES})`);
    
    // Step 2: Generate page URLs
    logger.info('Step 2: Generating page URLs...');
    const pageUrls = generatePageUrls(maxPage);
    logger.info(`Generated ${pageUrls.length} URLs`);
    
    // Step 3: Scrape pages
    logger.info('Step 3: Scraping pages...');
    const allProducts = [];
    let successCount = 0;
    let failureCount = 0;
    
    for (let i = 0; i < pageUrls.length; i++) {
      const pageNum = i + 1;
      const url = pageUrls[i];
      
      try {
        logger.info(`Scraping page ${pageNum}/${pageUrls.length}`);
        
        // Fetch page
        const html = await fetchPageWithRetry(url, config.RETRY_ATTEMPTS);
        
        // Extract products
        const products = extractProducts(html, url, batchStamp, pageNum);
        
        if (products.length > 0) {
          allProducts.push(...products);
          successCount++;
          
          logger.info(`✓ Page ${pageNum}: ${products.length} products extracted`);
          
          // Show sample product
          const sample = products[0];
          logger.info(`  Sample: ${sample.product_title} | ${sample.price_current} грн | ${sample.pack_qty}${sample.pack_unit}`);
        } else {
          logger.warn(`✗ Page ${pageNum}: No products extracted`);
        }
        
        // Log to file
        appendLog({
          ts: new Date().toISOString(),
          step: 'PARSE',
          stage: `page_${pageNum}/${pageUrls.length}`,
          message: `Extracted ${products.length} products`,
          url: url,
          status: 'success',
        });
        
        // Delay between requests
        if (i < pageUrls.length - 1) {
          await sleep(config.REQUEST_DELAY);
        }
        
      } catch (error) {
        failureCount++;
        logger.error(`✗ Page ${pageNum}: ${error.message}`);
        
        appendLog({
          ts: new Date().toISOString(),
          step: 'ERROR',
          stage: `page_${pageNum}`,
          message: error.message,
          url: url,
          status: 'failed',
        });
      }
    }
    
    // Step 4: Save results
    logger.info('Step 4: Saving results...');
    
    if (allProducts.length > 0) {
      saveToCSV(allProducts);
      logger.info(`✓ Saved ${allProducts.length} products to CSV`);
      
      appendLog({
        ts: new Date().toISOString(),
        step: 'WRITE',
        stage: 'save_csv',
        message: `Written ${allProducts.length} products`,
        url: 'N/A',
        status: 'success',
      });
    } else {
      logger.warn('No products to save');
    }
    
    // Step 5: Summary
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
    
    logger.info('='.repeat(80));
    logger.info('SCRAPER COMPLETED');
    logger.info(`Total products: ${allProducts.length}`);
    logger.info(`Pages success: ${successCount}`);
    logger.info(`Pages failed: ${failureCount}`);
    logger.info(`Elapsed time: ${elapsed}s`);
    logger.info('='.repeat(80));
    
    appendLog({
      ts: new Date().toISOString(),
      step: 'DONE',
      stage: 'runSilpoScraper',
      message: `total_products=${allProducts.length}, success=${successCount}, failures=${failureCount}, elapsed=${elapsed}s`,
      url: 'N/A',
      status: 'success',
    });
    
  } catch (error) {
    logger.error('CRITICAL ERROR: ' + error.message);
    logger.error(error.stack);
    
    appendLog({
      ts: new Date().toISOString(),
      step: 'CRITICAL_ERROR',
      stage: 'runSilpoScraper',
      message: error.message + '\n' + error.stack,
      url: 'N/A',
      status: 'failed',
    });
    
    process.exit(1);
  }
}

/**
 * Find last page from first page pagination
 */
async function findLastPage() {
  try {
    const html = await fetchPageWithRetry(config.BASE_URL, config.RETRY_ATTEMPTS);
    
    // Find max page from pagination
    const patterns = [
      /[?&]page=(\d+)/g,
      /<a[^>]*href="[^"]*page=(\d+)[^"]*"[^>]*>\s*(\d+)\s*<\/a>/gi,
      /page[^0-9]*(\d+)[^0-9]*(?:of|з|\/|total)/gi,
    ];
    
    let maxPage = 1;
    
    for (const pattern of patterns) {
      let match;
      while ((match = pattern.exec(html)) !== null) {
        const pageNum = parseInt(match[1]);
        if (pageNum > maxPage && pageNum <= config.MAX_PAGES) {
          maxPage = pageNum;
        }
      }
    }
    
    // Limit to MAX_PAGES
    return Math.min(maxPage, config.MAX_PAGES);
    
  } catch (error) {
    logger.error(`Failed to find last page: ${error.message}`);
    // Default to small number if detection fails
    return Math.min(10, config.MAX_PAGES);
  }
}

/**
 * Generate page URLs
 */
function generatePageUrls(maxPage) {
  const urls = [];
  
  for (let p = 1; p <= maxPage; p++) {
    if (p === 1) {
      urls.push(config.BASE_URL);
    } else {
      urls.push(`${config.BASE_URL}?page=${p}`);
    }
  }
  
  return urls;
}

/**
 * Run scraper if called directly
 */
if (require.main === module) {
  runSilpoScraper().catch(error => {
    logger.error('Fatal error: ' + error.message);
    process.exit(1);
  });
}

module.exports = {
  runSilpoScraper,
  findLastPage,
  generatePageUrls,
};
