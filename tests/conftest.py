"""Общие фикстуры pytest."""

import os

# Ensure automated tests run with mocked deterministic client without external network hits
os.environ["GEMINI_API_KEY"] = "mock_test_key"
