DIGITS = [str(x) for x in range(10)]


class BencodeParser:
    @staticmethod
    def parse(source):
        if isinstance(source, str):
            source = source.encode()

        content = []
        index = 0
        while index < len(source):
            extracted, index = BencodeParser._continue_parsing(
                source, index)
            content.append(extracted)
        return content

    @staticmethod
    def _continue_parsing(source, index):
        if index > len(source):
            return None, index
        symbol = chr(source[index])
        if symbol == 'i':
            return BencodeParser._parse_int(source, index + 1)
        elif symbol == 'l':
            return BencodeParser._parse_list(source, index + 1)
        elif symbol == 'd':
            return BencodeParser._parse_dictionary(source, index + 1)
        elif symbol in DIGITS:
            return BencodeParser._parse_string(source, index)
        else:
            raise Exception("Error in bencode: byte № " + str(index) +
                            " value " + str(source[index]))

    @staticmethod
    def _parse_int(source, index):
        return BencodeParser._parse_number(
            source, index, end_symbol='e', name="integer number")

    @staticmethod
    def _parse_number(source, index, end_symbol=" ", name="int"):
        number = 0
        mul = 1
        was_digits = False
        symbol = chr(source[index])
        if symbol == '-':
            mul = -1
            index += 1
        while index < len(source):
            symbol = chr(source[index])
            if symbol in DIGITS:
                number = number * 10 + int(symbol)
                was_digits = True
            elif symbol == end_symbol:
                break
            else:
                raise Exception("Error in bencode: incorrect "
                                "symbol in " + name)
            index += 1
        else:
            raise Exception("Error in bencode: unexpected end of "
                            "source during reading " + name)
        if not was_digits:
            raise Exception("Error in bencode: empty " + name)
        return number * mul, index + 1

    @staticmethod
    def _parse_string(source, index):
        count, index = BencodeParser._get_string_length(source, index)
        extracted, index = BencodeParser._get_string(
            source, index, count)
        return extracted, index

    @staticmethod
    def _get_string(source, index, count):
        if index + count > len(source):
            raise Exception("Error in bencode: unexpected end of "
                            "source during reading string")
        return source[index:index + count], index + count

    @staticmethod
    def _get_string_length(source, index):
        return BencodeParser._parse_number(
            source, index, end_symbol=':', name="string length")

    @staticmethod
    def _parse_list(source, index):
        extracted_sequence, index = BencodeParser._parse_sequence(
            source, index, name="list")
        return extracted_sequence, index

    @staticmethod
    def _parse_sequence(source, index, name):
        array = []
        while index < len(source):
            symbol = chr(source[index])
            if symbol == 'e':
                break
            extracted, index = BencodeParser._continue_parsing(
                source, index)
            if extracted is None:
                break
            array.append(extracted)
        else:
            raise Exception("Error in bencode: unexpected end "
                            "of source during reading " + name)
        return array, index + 1

    @staticmethod
    def _parse_dictionary(source, index):
        extracted_sequence, index = BencodeParser._parse_sequence(
            source, index, "dictionary")
        dictionary = {}
        for i in range(len(extracted_sequence)):
            elem = extracted_sequence[i]
            if i % 2 == 0:
                BencodeParser._is_key_string(elem)
            else:
                prev_elem = extracted_sequence[i - 1]
                dictionary[prev_elem] = elem
        if len(extracted_sequence) % 2 == 1:
            raise Exception('Error in bencode: dictionary key "' +
                            extracted_sequence[-1].decode() + '" has no value')
        return dictionary, index

    @staticmethod
    def _is_key_string(key):
        if not isinstance(key, bytes):
            raise Exception('Error in bencode: key: "' + str(key) +
                            '" is not a string, so it cannot be '
                            'dictionary key')
