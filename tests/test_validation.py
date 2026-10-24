import unittest
from radar.validation import is_valid_mint

class ValidationTests(unittest.TestCase):
    def test_key_shapes(self):
        self.assertTrue(is_valid_mint('1' * 32))
        self.assertTrue(is_valid_mint('So11111111111111111111111111111111111111112'))
    def test_bad_symbols(self):
        self.assertFalse(is_valid_mint('O' * 44))
        self.assertFalse(is_valid_mint('0' * 32))
    def test_bad_size(self):
        self.assertFalse(is_valid_mint('1' * 31))
        self.assertFalse(is_valid_mint('1' * 33))
        self.assertFalse(is_valid_mint(''))
