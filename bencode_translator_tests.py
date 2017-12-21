from bencode_translator import BencodeTranslator
import unittest


class BencodeTranslatorTests(unittest.TestCase):
    def test_positive_int(self):
        result = BencodeTranslator.translate_to_bencode(12)
        self.assertEqual(result, "i12e")

    def test_negative_int(self):
        result = BencodeTranslator.translate_to_bencode(-12)
        self.assertEqual(result, "i-12e")

    def test_zero(self):
        result = BencodeTranslator.translate_to_bencode(0)
        self.assertEqual(result, "i0e")

    def test_str(self):
        result = BencodeTranslator.translate_to_bencode("abcde")
        self.assertEqual(result, "5:abcde")

    def test_empty_str(self):
        result = BencodeTranslator.translate_to_bencode("")
        self.assertEqual(result, "0:")

    def test_list(self):
        result = BencodeTranslator.translate_to_bencode(["abc", 10])
        self.assertEqual(result, "l3:abci10ee")

    def test_empty_list(self):
        result = BencodeTranslator.translate_to_bencode([])
        self.assertEqual(result, "le")

    def test_complex_list(self):
        result = BencodeTranslator.translate_to_bencode([
            "ab", 10, [7, "hello", {"world": "!"}, ["a", "b", "c"]]])
        self.assertEqual(result, "l2:abi10eli7e5:hellod5:world1:!el1:a1:b1:ceee")

    def test_dict(self):
        result = BencodeTranslator.translate_to_bencode({"abc": 10})
        self.assertEqual(result, "d3:abci10ee")

    def test_empty_dict(self):
        result = BencodeTranslator.translate_to_bencode(dict())
        self.assertEqual(result, "de")

    def test_complex_dict(self):
        result = BencodeTranslator.translate_to_bencode({
            "abc": 10,
            "dict": {"abc": "def", "n": 15},
            "hello": "world",
            "list": ["hello", {"a": "b"}]
        })
        self.assertEqual(result, "d3:abci10e"
                                 "4:dictd3:abc3:def1:ni15ee"
                                 "5:hello5:world4:"
                                 "listl5:hellod1:a1:beee")