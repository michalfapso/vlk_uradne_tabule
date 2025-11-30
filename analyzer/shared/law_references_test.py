import unittest
import json
import os

# Import the functions to be tested
from .law_references import find_law_references_advanced

# --- Mock Data ---
# This registry is still needed for the find_law_references_advanced function to work
MOCK_LAW_REGISTRY = {
    "543/2002": {
        "names": [
            "(?:NR\s+SR\s+)?(?:č\.\s*)?543/2002\s*(?:Z\.\s?z\.)?",
            "o\s+ochrane\s+pr[ií]rody(?:\s+a\s+krajiny)?",
            "ZOPK",
            "ZOPaK",
            "(?:(?:zákon[ea]?\s+)?(?:o\s+)?)?OPaK"
        ]
    },
    "71/1967": {
        "names": [
            "(?:č\.\s*)?71/1967\s*(?:(?:Z\.\s?z\.)|(?:[Zz]b))?",
            "o\s+spr[aá]vnom\s+konan[ií]",
            "spr[aá]vny\s+poriadok",
            "spr[aá]vneho\s+poriadku"
        ]
    }
}

# --- Unmatched References Log ---
unmatched_references_log = []

def log_unmatched_reference(text_input, reference):
    """Logs a reference that could not be matched to a known law."""
    unmatched_references_log.append({
        "input_text": text_input,
        "unmatched_reference": reference
    })

class TestLawReferenceParsing(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        self.law_registry = MOCK_LAW_REGISTRY
        script_dir = os.path.dirname(__file__)
        test_cases_path = os.path.join(script_dir, '../../tests/law_references_test_cases.json')
        with open(test_cases_path, 'r', encoding='utf-8') as f:
            self.test_cases = json.load(f)
        
        # Reset the log before each test run
        global unmatched_references_log
        unmatched_references_log = []

    def test_parse_references_from_json(self):
        """
        Dynamically tests reference parsing based on law_references_test_cases.json.
        """
        for i, test_case in enumerate(self.test_cases):
            with self.subTest(f"Test Case #{i+1}: {test_case['in'][:50]}..."):
                
                actual_refs = find_law_references_advanced(test_case['in'], self.law_registry)
                expected_refs = test_case['out']

                self.assertEqual(len(actual_refs), len(expected_refs), 
                                 f"Expected {len(expected_refs)} references, but found {len(actual_refs)}.")

                for actual, expected in zip(actual_refs, expected_refs):
                    # Check paragraph
                    self.assertEqual(actual.get('paragraf_start'), expected.get('par'), "Paragraph start mismatch.")
                    
                    # Check section ranges
                    if 'ods' in expected:
                        odseky = expected['ods'].split('-')
                        self.assertEqual(actual.get('odsek_start'), odseky[0], "Odsek start mismatch.")
                        if len(odseky) > 1:
                            self.assertEqual(actual.get('odsek_end'), odseky[1], "Odsek end mismatch.")

                    # Check law ID
                    if 'zak' in expected:
                        self.assertEqual(actual.get('zakon_id'), expected.get('zak'), "Zakon ID mismatch.")
                    
                    # Check letter ranges
                    if 'pis' in expected:
                        pismena = expected['pis'].split('-')
                        self.assertEqual(actual.get('pismeno_start'), pismena[0], "Pismeno start mismatch.")
                        if len(pismena) > 1:
                            self.assertEqual(actual.get('pismeno_end'), pismena[1], "Pismeno end mismatch.")

                    # Check for unmatched law names and log them
                    if 'unmatched_name' in expected:
                        self.assertIsNone(actual.get('zakon_id'), "Zakon ID should be None for unmatched reference.")
                        self.assertIn('zakon_refname', actual, "zakon_refname should be present for unmatched reference.")
                        self.assertEqual(actual['zakon_refname'], expected['unmatched_name'])
                        log_unmatched_reference(test_case['in'], actual)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

    print("\n--- Log nezhodných referencií ---")
    if unmatched_references_log:
        for item in unmatched_references_log:
            print(json.dumps(item, indent=2, ensure_ascii=False))
    else:
        print("Žiadne nezhodné referencie neboli zaznamenané.")