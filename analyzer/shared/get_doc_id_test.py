import pytest
import json
import os
from get_doc_id import get_doc_id

# Load common test cases from JSON file
def load_common_test_cases():
    # Construct path relative to this test file
    # This file is in 'analyzer/', shared_test_cases.json is in 'tests/'
    # So, ../tests/shared_test_cases.json
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, '..', 'tests', 'get_doc_id_test_cases.json')
    with open(json_path, 'r') as f:
        return [tuple(item) for item in json.load(f)]

COMMON_TEST_CASES = load_common_test_cases()

@pytest.mark.parametrize("doc_url, expected_id", COMMON_TEST_CASES)
def test_get_doc_id_specific_urls_python(doc_url, expected_id):
    print(f"Testing URL: {doc_url} with expected ID: {expected_id}")
    assert get_doc_id(doc_url) == expected_id

