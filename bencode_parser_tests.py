import re
from unittest import TestCase
from bencode_parser import BencodeParser


class LoaderTests(TestCase):
    def test_string_parse_correct(self):
        expected = "abcde"
        source = "5:" + expected
        content = BencodeParser.parse(source)
        self.assertEqual(content[0], expected)

    def test_string_parse_empty(self):
        expected = ""
        source = "0:" + expected
        content = BencodeParser.parse(source)
        self.assertEqual(content[0], expected)

    def test_string_parse_incorrect_symbol_in_length(self):
        source = "1O:somestring"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: incorrect symbol in string length"),
                               BencodeParser.parse, source)

    def test_string_parse_incorrect_length(self):
        source = "15:string"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: unexpected end of "
            "source during reading string"),
                               BencodeParser.parse, source)

    def test_string_parse_incorrect_negative_length(self):
        source = "-5:abcde"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode"), BencodeParser.parse, source)

    def test_string_parse_no_end_of_length(self):
        source = "15"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: unexpected end of "
            "source during reading string length"),
                               BencodeParser.parse, source)

    def test_int_parse_correct(self):
        expected = 100500
        source = 'i' + str(expected) + 'e'
        content = BencodeParser.parse(source)
        self.assertEqual(content[0], expected)

    def test_int_parse_negative(self):
        expected = -100500
        source = 'i' + str(expected) + 'e'
        content = BencodeParser.parse(source)
        self.assertEqual(content[0], expected)

    def test_int_parse_zero(self):
        expected = 0
        source = 'i' + str(expected) + 'e'
        content = BencodeParser.parse(source)
        self.assertEqual(content[0], expected)

    def test_int_parse_incorrect_without_ending(self):
        expected = 100500
        source = 'i' + str(expected)
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: unexpected end of "
            "source during reading integer number"),
                               BencodeParser.parse, source)

    def test_int_parse_incorrect_symbol(self):
        source = 'i12343:abc'
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: incorrect symbol in integer number"),
                   BencodeParser.parse, source)
        source = 'i2.5e'
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: incorrect symbol in integer number"),
                   BencodeParser.parse, source)

    def test_int_parse_incorrect_empty_number(self):
        source = 'ie'
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: empty integer number"),
                   BencodeParser.parse, source)
        source = 'i-e'
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: empty integer number"),
                   BencodeParser.parse, source)

    def test_list_parse_correct_int(self):
        expected = [125]
        source = 'li125ee'
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_string(self):
        string = "abcde"
        expected = [string]
        source = "l5:" + string + "e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_empty_correct(self):
        expected = []
        source = 'le'
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_two_elements_string_and_int(self):
        string = "abcde"
        expected = [string, 100]
        source = "l5:" + string + "i100e" + "e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_two_strings(self):
        str1 = "abcde"
        str2 = "something"
        expected = [str1, str2]
        source = "l5:" + str1 + "9:" + str2 + "e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_two_integers(self):
        expected = [123, -15]
        source = "l" + "i123e" + "i-15e" + "e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_two_inner_list(self):
        expected = [[1], [2]]
        source = "l" + "li1ee" + "li2ee" + "e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_correct_int_string_and_inner_list(self):
        expected = [128, "hello", [32, "hi"]]
        source = "l" + "i128e" + "5:hello" + "l" + "i32e" + "2:hi" + "e" + "e"
        content = BencodeParser.parse(source)
        self.assertListEqual(content[0], expected)

    def test_list_parse_incorrect_no_ending(self):
        source = "li1234e"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: unexpected end of source during "
            "reading list"),
                   BencodeParser.parse, source)

    def test_dict_parse_correct_string_int(self):
        expected = {"key123": 456}
        source = "d" + "6:key123" + "i456e" + "e"
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_correct_string_string(self):
        key = "some_key"
        value = "some_value"
        expected = {key: value}
        source = "d8:" + key + "10:" + value + "e"
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_empty_correct(self):
        expected = {}
        source = 'de'
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_correct_two_pairs(self):
        key_1 = "key1"
        key_2 = "key2"
        value_1 = "value1"
        value_2 = "value2"
        expected = {key_1: value_1, key_2: value_2}
        source = "d" + "4:" + key_1 + "6:" + value_1 + \
                 "4:" + key_2 + "6:" + value_2 + "e"
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_correct_list_value(self):
        key = "key"
        value_1 = "some_value"
        value_2 = "one_more_value"
        expected = {key: [value_1, value_2]}
        source = "d3:" + key + "l10:" + value_1 + \
                 "14:" + value_2 + "ee"
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_correct_dict_value(self):
        key_1 = "key1"
        key_2 = "key2"
        value = "inner_value"
        expected = {key_1: {key_2: value}}
        source = "d" + "4:" + key_1 + "d" + "4:" + key_2 + \
                 "11:" + value + "ee"
        content = BencodeParser.parse(source)
        self.assertDictEqual(content[0], expected)

    def test_dict_parse_incorrect_no_ending(self):
        source = "d" + "3:key" + "5:value"
        self.assertRaisesRegex(Exception, re.compile(
            "Error in bencode: unexpected end of source during "
            "reading dictionary"),
                   BencodeParser.parse, source)

    def test_dict_parse_incorrect_key_without_value(self):
        source = "d" + "4:key1" + "i12345e" + "10:lonely_key" + "e"
        self.assertRaisesRegex(Exception, re.compile(
            r'Error in bencode: dictionary key "\w+" has no value'),
                               BencodeParser.parse, source)

    def test_dict_parse_incorrect_not_string_key(self):
        source = "d" + "i100e" + "5:value" + "e"
        self.assertRaisesRegex(Exception, re.compile(
            r'Error in bencode: key: "\w+" is not a string, '
            r'so it cannot be dictionary key'),
                               BencodeParser.parse, source)
