import re
from unittest import TestCase
from bencode import BencodeParser, BencodeTranslator


class BencodeParserTests(TestCase):
    def test_string_parse_correct(self):
        expected = "abcde"
        source = "5:" + expected
        content = BencodeParser.parse(source)
        self.assertEqual(content[0], expected.encode())

    def test_string_parse_empty(self):
        expected = b""
        source = b"0:" + expected
        content = BencodeParser.parse(source)
        self.assertEqual(content[0], expected)

    def test_string_parse_incorrect_symbol_in_length(self):
        source = b"1O:somestring"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: incorrect symbol in string length"),
                               BencodeParser.parse, source)

    def test_string_parse_incorrect_length(self):
        source = b"15:string"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: unexpected end of "
            "source during reading string"),
                               BencodeParser.parse, source)

    def test_string_parse_incorrect_negative_length(self):
        source = b"-5:abcde"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode"), BencodeParser.parse, source)

    def test_string_parse_no_end_of_length(self):
        source = b"15"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: unexpected end of "
            "source during reading string length"),
                               BencodeParser.parse, source)

    def test_int_parse_correct(self):
        expected = 100500
        source = b'i' + str(expected).encode() + b'e'
        content = BencodeParser.parse(source)
        self.assertEqual(content[0], expected)

    def test_int_parse_negative(self):
        expected = -100500
        source = b'i' + str(expected).encode() + b'e'
        content = BencodeParser.parse(source)
        self.assertEqual(content[0], expected)

    def test_int_parse_zero(self):
        expected = 0
        source = b'i' + str(expected).encode() + b'e'
        content = BencodeParser.parse(source)
        self.assertEqual(content[0], expected)

    def test_int_parse_incorrect_without_ending(self):
        expected = 100500
        source = b'i' + str(expected).encode()
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: unexpected end of "
            "source during reading integer number"),
                               BencodeParser.parse, source)

    def test_int_parse_incorrect_symbol(self):
        source = b'i12343:abc'
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: incorrect symbol in integer number"),
                   BencodeParser.parse, source)
        source = b'i2.5e'
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: incorrect symbol in integer number"),
                   BencodeParser.parse, source)

    def test_int_parse_incorrect_empty_number(self):
        source = b'ie'
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: empty integer number"),
                   BencodeParser.parse, source)
        source = b'i-e'
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: empty integer number"),
                   BencodeParser.parse, source)

    def test_list_parse_correct_int(self):
        expected = [125]
        source = b'li125ee'
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_string(self):
        string = b"abcde"
        expected = [string]
        source = b"l5:" + string + b"e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_empty_correct(self):
        expected = []
        source = b'le'
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_two_elements_string_and_int(self):
        string = b"abcde"
        expected = [string, 100]
        source = b"l5:" + string + b"i100e" + b"e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_two_strings(self):
        str1 = b"abcde"
        str2 = b"something"
        expected = [str1, str2]
        source = b"l5:" + str1 + b"9:" + str2 + b"e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_two_integers(self):
        expected = [123, -15]
        source = b"l" + b"i123e" + b"i-15e" + b"e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_two_inner_list(self):
        expected = [[1], [2]]
        source = b"l" + b"li1ee" + b"li2ee" + b"e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_int_string_and_inner_list(self):
        expected = [128, b"hello", [32, b"hi"]]
        source = b"l" + b"i128e" + b"5:hello" + \
                 b"l" + b"i32e" + b"2:hi" + b"e" + b"e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_incorrect_no_ending(self):
        source = b"li1234e"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: unexpected end of source during "
            "reading list"),
                   BencodeParser.parse, source)

    def test_dict_parse_correct_string_int(self):
        expected = {b"key123": 456}
        source = b"d" + b"6:key123" + b"i456e" + b"e"
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_correct_string_string(self):
        key = b"some_key"
        value = b"some_value"
        expected = {key: value}
        source = b"d8:" + key + b"10:" + value + b"e"
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_empty_correct(self):
        expected = {}
        source = b'de'
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_correct_two_pairs(self):
        key_1 = b"key1"
        key_2 = b"key2"
        value_1 = b"value1"
        value_2 = b"value2"
        expected = {key_1: value_1, key_2: value_2}
        source = b"d" + b"4:" + key_1 + b"6:" + value_1 + \
                 b"4:" + key_2 + b"6:" + value_2 + b"e"
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_correct_list_value(self):
        key = b"key"
        value_1 = b"some_value"
        value_2 = b"one_more_value"
        expected = {key: [value_1, value_2]}
        source = b"d3:" + key + b"l10:" + value_1 + \
                 b"14:" + value_2 + b"ee"
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_correct_dict_value(self):
        key_1 = b"key1"
        key_2 = b"key2"
        value = b"inner_value"
        expected = {key_1: {key_2: value}}
        source = b"d" + b"4:" + key_1 + \
                 b"d" + b"4:" + key_2 + b"11:" + value + b"ee"
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_incorrect_no_ending(self):
        source = b"d" + b"3:key" + b"5:value"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: unexpected end of source during "
            "reading dictionary"),
                   BencodeParser.parse, source)

    def test_dict_parse_incorrect_key_without_value(self):
        source = b"d" + b"4:key1" + b"i12e" + b"10:lonely_key" + b"e"
        self.assertRaisesRegex(Exception, re.compile(
            r'Error in bencode: dictionary key "\w+" has no value'),
                               BencodeParser.parse, source)

    def test_dict_parse_incorrect_not_string_key(self):
        source = b"d" + b"i100e" + b"5:value" + b"e"
        self.assertRaisesRegex(Exception, re.compile(
            r'Error in bencode: key: "\w+" is not a string, '
            r'so it cannot be dictionary key'),
                               BencodeParser.parse, source)


class BencodeTranslatorTests(TestCase):
    def test_positive_int(self):
        result = BencodeTranslator.translate_to_bencode(12)
        self.assertEqual(result, b"i12e")

    def test_negative_int(self):
        result = BencodeTranslator.translate_to_bencode(-12)
        self.assertEqual(result, b"i-12e")

    def test_zero(self):
        result = BencodeTranslator.translate_to_bencode(0)
        self.assertEqual(result, b"i0e")

    def test_str(self):
        result = BencodeTranslator.translate_to_bencode("abcde")
        self.assertEqual(result, b"5:abcde")

    def test_empty_str(self):
        result = BencodeTranslator.translate_to_bencode("")
        self.assertEqual(result, b"0:")

    def test_list(self):
        result = BencodeTranslator.translate_to_bencode(["abc", 10])
        self.assertEqual(result, b"l3:abci10ee")

    def test_empty_list(self):
        result = BencodeTranslator.translate_to_bencode([])
        self.assertEqual(result, b"le")

    def test_complex_list(self):
        result = BencodeTranslator.translate_to_bencode([
            "ab", 10, [7, "hello", {"world": "!"}, ["a", "b", "c"]]])
        self.assertEqual(result, b"l2:abi10eli7e5:hellod5:world1:!el1:a1:b1:ceee")

    def test_dict(self):
        result = BencodeTranslator.translate_to_bencode({"abc": 10})
        self.assertEqual(result, b"d3:abci10ee")

    def test_empty_dict(self):
        result = BencodeTranslator.translate_to_bencode(dict())
        self.assertEqual(result, b"de")

    def test_complex_dict(self):
        result = BencodeTranslator.translate_to_bencode({
            "abc": 10,
            "dict": {"abc": "def", "n": 15},
            "hello": "world",
            "list": ["hello", {"a": "b"}]
        })
        self.assertEqual(result, b"d3:abci10e"
                                 b"4:dictd3:abc3:def1:ni15ee"
                                 b"5:hello5:world4:"
                                 b"listl5:hellod1:a1:beee")
