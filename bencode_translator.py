def _add_int(source, collection):
    collection.append(b"i")
    collection.append(str(source).encode())
    collection.append(b"e")


def _add_str_or_bytes(source, collection):
    collection.append(str(len(source)).encode())
    collection.append(b":")
    if isinstance(source, str):
        collection.append(source.encode())
    else:
        collection.append(source)


def _add_list(source, collection):
    collection.append(b"l")
    for elem in source:
        _translate(elem, collection)
    collection.append(b"e")


def _add_dict(source, collection):
    collection.append(b"d")
    keys = list(source.keys())
    keys.sort()
    for key in keys:
        if not isinstance(key, (str, bytes)):
            raise TypeError("Keys in bencode dictionary "
                            "can be strings or bytes only")
        _translate(key, collection)
        _translate(source[key], collection)
    collection.append(b"e")


def _translate(source, collection):
    if isinstance(source, int):
        _add_int(source, collection)
    elif isinstance(source, (str, bytes)):
        _add_str_or_bytes(source, collection)
    elif isinstance(source, list):
        _add_list(source, collection)
    elif isinstance(source, dict):
        _add_dict(source, collection)
    else:
        raise TypeError("Cannot convert to bencode object "
                    "with type: " + str(type(source)))


class BencodeTranslator:
    @staticmethod
    def translate_to_bencode(source):
        collection = []
        _translate(source, collection)
        result = b"".join(collection)
        return result

    @staticmethod
    def print_bencode(obj, depth=0):
        if isinstance(obj, (int, bytes)):
            print("\t" * depth + str(obj))
        elif isinstance(obj, list):
            print("\t" * depth + "[")
            for elem in obj:
                BencodeTranslator.print_bencode(elem, depth + 1)
            print("\t" * depth + "]")
        elif isinstance(obj, dict):
            print("\t" * depth + "{")
            keys = list(obj.keys())
            keys.sort()
            for key in keys:
                print("\t" * (depth + 1) + str(key) + " : ")
                BencodeTranslator.print_bencode(obj[key], depth + 2)
            print("\t" * depth + "}")
