import hashlib
from pathlib import Path
import queue

from bencode_parser import BencodeParser
from bencode_translator import BencodeTranslator
from tracker_speaker import TrackerConnection
from peer_speaker_thread import PeerConnection


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


def _read_source_from_file(torrent_file_path):
    with open(torrent_file_path, 'rb') as meta:
        source = meta.read()
    return source


class Loader:
    @staticmethod
    def get_peer_id():
        return ("-" + "MY" + "0001" + "-" + "123456789012").encode()

    def __init__(self, file_path):
        """takes .torrent file"""
        if not isinstance(file_path, str):
            raise TypeError("Loader takes string as file_path")
        self.torrent_file_path = file_path
        _check_file(file_path)
        source = _read_source_from_file(file_path)
        self._content = BencodeParser.parse(source)[0]
        self._info_hash = None
        self._tracker = TrackerConnection(self)
        self.is_working = False

    def download(self):
        self.is_working = True
        self._tracker.start()

    def get_info_hash(self):
        if self._info_hash is None:
            hasher = hashlib.sha1()
            info = self._content[b"info"]
            info_bencode = BencodeTranslator.translate_to_bencode(info)
            #start = self._source.find(b"infod")
            #finish = self._source.find(b"9:publisher")
            #info_bencode = b"d" + self._source[start+5:finish]
            hasher.update(info_bencode)

            self._info_hash = hasher.digest()
        return self._info_hash

