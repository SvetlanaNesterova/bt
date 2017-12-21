class BencodeTranslator:
    @staticmethod
    def translate_to_bencode(source):
        collection = []
        BencodeTranslator._translate(source, collection)
        result = "".join(collection)
        return result

    @staticmethod
    def _translate(source, collection):
        if isinstance(source, int):
            collection.append("i")
            collection.append(str(source))
            collection.append("e")
        elif isinstance(source, str):
            collection.append(str(len(source)))
            collection.append(":")
            collection.append(source)
        elif isinstance(source, list):
            collection.append("l")
            for elem in source:
                BencodeTranslator._translate(elem, collection)
            collection.append("e")
        elif isinstance(source, dict):
            collection.append("d")
            keys = list(source.keys())
            keys.sort()
            for key in keys:
                if not isinstance(key, str):
                    raise TypeError("Keys in bencode dictionary can be"
                                    "strings only")
                BencodeTranslator._translate(key, collection)
                BencodeTranslator._translate(source[key], collection)
            collection.append("e")
        else:
            raise TypeError("Cannot convert to bencode object "
                        "with type: " + str(type(source)))

