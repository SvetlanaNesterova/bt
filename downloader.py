import random
from pathlib import Path
import requests
import hashlib
from bencode_parser import BencodeParser
from bencode_translator import BencodeTranslator

class Loader:
    @staticmethod
    def get_peer_id():
        # Hmmmmm ?!
        return "76128987659298765123"

    def __init__(self, file_path):
        """takes .torrent file"""
        if not isinstance(file_path, str):
            raise TypeError("Loader takes string as file_path")
        self.torrent_file_path = file_path
        self._check_file(self.torrent_file_path)

    @staticmethod
    def _check_file(file_path):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError("No such file")
        if not path.is_file():
            raise ValueError("No such file. "
                             "You should specify file, not directory")
        if path.suffix != ".torrent":
            raise ValueError("Loader takes .torrent file, but file "
                             "extension was: " + path.suffix)

    def download(self):
        self._check_file(self.torrent_file_path)
        self._source = self._read_source_from_file()
        self._content = BencodeParser.parse(self._source)[0]
        self._get_peers(self._content)

    def _read_source_from_file(self):
        # кодировка ? utf-8 полетела
        # UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc0 in position 825: invalid start byte
        with open(self.torrent_file_path, 'rb') as meta:
            source = meta.read()
        return source

    def _get_peers(self, content):
        tracker_url = content[b"announce"]
        self._info_hash = self._get_info_hash()
        result = self._try_connect_tracker(tracker_url)
        #if result is not None:
        #    return result
        for tracker_url in content[b"announce-list"]:
            result = self._try_connect_tracker(tracker_url[0])
        #    if result is not None:
        #        return result
        raise ConnectionError("Failed to connect with any of "
                              "torrent trackers")

    def _get_info_hash(self):
        hasher = hashlib.sha1()
        #info = self._content["info"]
        #info_bencode = BencodeTranslator.translate_to_bencode(info)
        start = self._source.find(b"infod")
        finish = self._source.find(b"9:publisher")
        info_bencode = b"d" + self._source[start+5:finish]
        hasher.update(info_bencode)
        return hasher.digest()

    def _try_connect_tracker(self, tracker_url):
        if tracker_url.startswith(b"udp"):
            pass
        elif tracker_url.startswith(b"http"):
            print("Try " + str(tracker_url))
            info_hash = self._info_hash
            peer_id = Loader.get_peer_id()
            #ip =
            port = random.Random().randint(0, 9) + 6889 # попробовать другие
            uploaded = "0"
            downloaded = "0"
            left = str(self._content[b'info'][b'piece length'] * \
                   self._content[b'info'][b'length'])
            event = "started"
            params = {
                "info_hash": info_hash,
                "peer_id": peer_id,
                "port": port,
                "uploaded": uploaded,
                "downloaded": downloaded,
                "left": left,
                "event": event,
            }
            try:
                r = requests.get(tracker_url, params=params)
                try:
                    self.print_bencode(BencodeParser.parse(r.content))
                    return r
                except Exception as e:
                    print("EXCEPTION")
                    print(e)
                    return None
            except Exception as e:
                print("BAD REQUEST")
                print(e)
                return None

    def print_bencode(self, obj, depth=0):
        if isinstance(obj, (int, bytes)):
            print("\t" * depth + str(obj))
        elif isinstance(obj, list):
            print("\t" * depth + "[")
            for elem in obj:
                self.print_bencode(elem, depth + 1)
            print("\t" * depth + "]")
        elif isinstance(obj, dict):
            print("\t" * depth + "{")
            keys = list(obj.keys())
            keys.sort()
            for key in keys:
                print("\t" * (depth + 1) + str(key) + " : ")
                self.print_bencode(obj[key], depth + 2)
            print("\t" * depth + "}")

    def _escape_bytes(self, source):
        digits = [chr(c) for c in range(ord('0'), ord('9') + 1)]
        good_chars = [char for char in "$-_.+!*'(),"] + \
                     [chr(c) for c in range(ord('a'), ord('z') + 1)] + \
                     [chr(c) for c in range(ord('A'), ord('Z') + 1)] + \
                     digits
        result = ""
        for elem in source:
            if not isinstance(elem, str):
                char = chr(elem)
            else:
                char = elem
            if char in good_chars:
                result += char
            else:
                hex_code = hex(ord(char))[2:]
                if len(hex_code) == 1:
                    hex_code = '0' + hex_code
                result += '%' + hex_code
        print(result)
        result = ""
        for elem in source:
            if not isinstance(elem, str):
                char = chr(elem)
            else:
                char = elem
            if char in good_chars:
                result += char
            else:
                hex_code = hex(ord(char))[2:]
                if len(hex_code) == 1:
                    hex_code = '0' + hex_code
                if hex_code[0] not in digits:
                    n = chr(ord(hex_code[0]) - ord("a") + ord("A"))
                    hex_code = n + hex_code[1]
                if hex_code[1] not in digits:
                    n = chr(ord(hex_code[1]) - ord("a") + ord("A"))
                    hex_code = hex_code[0] + n
                result += '%' + hex_code
        print(result)
        return result



