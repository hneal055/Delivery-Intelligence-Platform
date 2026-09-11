const fs = require('fs');
const path = require('path');

const TARGET_DIR = path.join(__dirname, '../src');
const IP_REGEX = /192\.168\.\d{1,3}\.\d{1,3}/g;

function walkDir(dir, callback) {
  fs.readdirSync(dir).forEach(file => {
    const filePath = path.join(dir, file);
    if (fs.statSync(filePath).isDirectory()) {
      walkDir(filePath, callback);
    } else if (filePath.endsWith('.js') || filePath.endsWith('.json')) {
      callback(filePath);
    }
  });
}

let hasErrors = false;

walkDir(TARGET_DIR, (filePath) => {
  const content = fs.readFileSync(filePath, 'utf8');
  
  // Check for hardcoded local network IPs
  if (IP_REGEX.test(content)) {
    console.error(`[ValidationError] Hardcoded local IP detected in: ${filePath}`);
    hasErrors = true;
  }

  // Check app.json validity
  if (filePath.endsWith('app.json')) {
    try {
      JSON.parse(content);
    } catch (e) {
      console.error(`[ValidationError] Invalid JSON structure in app.json: ${filePath}`);
      hasErrors = true;
    }
  }
});

if (hasErrors) {
  console.error('\n❌ Project validation failed! Please fix the errors above before committing or building.');
  process.exit(1);
} else {
  console.log('✅ Project validation passed successfully. No hardcoded IPs or config errors found.');
  process.exit(0);
}