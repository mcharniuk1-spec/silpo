// fetcher.js - HTTP request handling

const axios = require('axios');
const config = require('./config');

const logger = {
  info: (msg) => console.log(`[INFO] ${new Date().toISOString()} ${msg}`),
  warn: (msg) => console.warn(`[WARN] ${new Date().toISOString()} ${msg}`),
  error: (msg) => console.error(`[ERROR] ${new Date().toISOString()} ${msg}`),
};

/**
 * Fetch page with retries
 */
async function fetchPageWithRetry(url, maxAttempts = 3) {
  let lastError = null;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      logger.info(`Fetching (attempt ${attempt}/${maxAttempts}): ${url}`);
      
      const response = await axios.get(url, {
        headers: {
          'User-Agent': config.USER_AGENT,
          'Accept-Language': 'uk,en;q=0.9,ru;q=0.8',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Cache-Control': 'no-cache',
          'Referer': 'https://silpo.ua/',
        },
        timeout: 10000,
      });
      
      if (response.status !== 200) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      if (!response.data || response.data.length < 1000) {
        throw new Error(`Empty/short response (${response.data.length} chars)`);
      }
      
      logger.info(`Success: fetched ${response.data.length} chars`);
      return response.data;
      
    } catch (error) {
      lastError = error;
      logger.warn(`Attempt ${attempt} failed: ${error.message}`);
      
      if (attempt < maxAttempts) {
        const delay = config.RETRY_DELAY * attempt;
        logger.info(`Waiting ${delay}ms before retry...`);
        await sleep(delay);
      }
    }
  }
  
  throw new Error(`Failed after ${maxAttempts} attempts: ${lastError.message}`);
}

/**
 * Sleep utility
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

module.exports = {
  fetchPageWithRetry,
  sleep,
  logger,
};
