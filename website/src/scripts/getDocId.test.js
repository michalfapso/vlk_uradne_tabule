import { getDocId } from './getDocId.js'; // Assuming getDocId.js is in the same directory
import fs from 'fs';
import { jest } from '@jest/globals'; // Import jest for spyOn
import path from 'path';
import { fileURLToPath } from 'url';

// Helper to get current directory in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load common test cases from JSON file
function loadCommonTestCases() {
    // Construct path relative to this test file
    // This file is in 'website/src/scripts/', shared_test_cases.json is in 'tests/'
    // So, ../../../tests/shared_test_cases.json
    const jsonPath = path.resolve(__dirname, '..', '..', '..', 'tests', 'get_doc_id_test_cases.json');
    const fileContent = fs.readFileSync(jsonPath, 'utf8');
    return JSON.parse(fileContent);
}

const COMMON_TEST_CASES = loadCommonTestCases();

describe('getDocId JavaScript', () => {
    test.each(COMMON_TEST_CASES)('getDocId(%s) should return %s', (docUrl, expectedId) => {
        // Suppress console.error for expected invalid URL parsing warnings during test
        const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
        expect(getDocId(docUrl)).toBe(expectedId);
        consoleErrorSpy.mockRestore();
    });
});

