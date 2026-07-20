# tests/conftest.py
import sys
import os

# Add project root to path so 'app' is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))