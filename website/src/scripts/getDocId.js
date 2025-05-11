import { URL } from 'url'; // Use 'url' module in Node.js
import path from 'path';   // Use 'path' module in Node.js
import crypto from 'crypto'; // Use 'crypto' module in Node.js

/**
 * Determines the document ID from a URL.
 * 1. Tries the 'subor' parameter.
 * 2. Tries the filename from the URL path if it starts with 'OU-'.
 * 3. If unsuccessful, returns a hash of the entire URL.
 * @param {string | null | undefined} docUrl - The document URL.
 * @returns {string | null} The document ID or null if none could be determined or input is invalid.
 */
function getDocId(docUrl) { // Using JS naming conventions (camelCase)
    if (!docUrl) {
        return null;
    }

    let parsedUrl;
    try {
        parsedUrl = new URL(docUrl);
    } catch (e) {
        // Handle invalid URL gracefully, maybe return null or a hash of the bad input?
        // Current Python code doesn't explicitly handle malformed URLs before parsing.
        // Let's follow the Python logic and let the hash step handle it if possible,
        // or return null if even hashing fails.
        console.error(`Warning: Could not parse URL ${docUrl}: ${e}`);
        // Proceeding to try hashing the potentially bad URL string as per Python's fallback
    }

    // 1. Check for 'subor' parameter
    // Note: URLSearchParams automatically handles multiple values, get returns first.
    if (parsedUrl && parsedUrl.searchParams.has('subor')) {
        const suborValue = parsedUrl.searchParams.get('subor');
        if (suborValue) { // Ensure the parameter has a non-empty value
             return suborValue;
        }
    }

    // 2. If filename starts with 'OU-', use it
    const urlPath = parsedUrl ? parsedUrl.pathname : ''; // Handle cases where parsedUrl failed
    if (urlPath) {
        const filenameWithExt = path.basename(urlPath);
        if (filenameWithExt && filenameWithExt.startsWith('OU-')) {
            const filenameWithoutExt = path.parse(filenameWithExt).name; // path.parse gives name and ext
            return filenameWithoutExt;
        }
    }

    // 3. If nothing above works, generate a hash from the URL string
    try {
        // Node.js crypto expects data, not bytes directly for string inputs,
        // but we need consistent hashing with Python's utf-8 encoding.
        // Using createHash and update with the string is equivalent to Python's hashlib.sha256(url_bytes).
        const hash = crypto.createHash('sha256').update(docUrl, 'utf8');
        const hexDig = hash.digest('hex');
        // Ensure the prefix is consistent across implementations
        return `urlhash_${hexDig.substring(0, 16)}`; // Use first 16 chars of hash
    } catch (e) {
        console.error(`Chyba pri generovaní hashu pre URL ${docUrl}: ${e}`); // Use console.error in JS
        return null;
    }
}

// Example Usage (JavaScript)
// console.log(getDocId("https://example.com/path/to/OU-document.pdf")); // OU-document
// console.log(getDocId("https://example.com/?subor=fileid123")); // fileid123
// console.log(getDocId("https://example.com/some/other/file.txt")); // urlhash_...
// console.log(getDocId(null)); // null
// console.log(getDocId("")); // null
// console.log(getDocId("htp://invalid-url")); // warning, urlhash_... (if hashing works)

export { getDocId }; // Export the function for use in other modules/tests