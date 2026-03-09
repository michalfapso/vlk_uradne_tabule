// Usage: node documentAnalysis_cli.js 'path/to/analysis.json'

import fs from 'node:fs';
import path from 'node:path';
import { isDataImportant, DEFAULT_REGEX_STRING } from './documentAnalysis.js';

// Get the path to analysis.json from command line arguments
const analysisPath = process.argv[2];

if (!analysisPath) {
    console.error('Usage: node scripts/classify.js <path-to-analysis.json>');
    process.exit(1);
}

try {
    const analysisData = JSON.parse(fs.readFileSync(analysisPath, 'utf8'));
    
    // The logic in documentAnalysis.js expects an object where the analysis 
    // is under the 'analyza' key, similar to how Astro prepares it.
    const docWrapper = {
        analyza: analysisData,
        nazov: analysisData.nazov || "Unknown" // analysis.json might not have the title
    };

    const regex = new RegExp(DEFAULT_REGEX_STRING, 'i');
    const important = isDataImportant(docWrapper, regex);

    console.log(important ? 'IMPORTANT' : 'UNIMPORTANT');
    process.exit(important ? 0 : 1); // Useful for shell scripting
} catch (error) {
    console.error(`Error processing file: ${error.message}`);
    process.exit(2);
}
