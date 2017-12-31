from pathlib import Path
from messages import get_sha_1_hash

from bencode_parser import BencodeParser
from bencode_translator import BencodeTranslator
from tracker_speaker import TrackerConnection
from pieces_allocator import Allocator


def _check_file(file_path: str):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError("No such file")
    if not path.is_file():
        raise ValueError("No such file. "
                         "You should specify file, not directory")
    if path.suffix != ".torrent":
        raise ValueError("Loader takes .torrent file, but file "
                         "extension was: " + path.suffix)


def _read_source_from_file(torrent_file_path: str):
    with open(torrent_file_path, 'rb') as meta:
        source = meta.read()
    return source


class Loader:
    @staticmethod
    def get_peer_id():
        return ("-" + "MY" + "0001" + "-" + "123456789012").encode()

    def __init__(self, torrent_file_path: str, save_file_path: str):
        """ takes .torrent file """
        if not isinstance(torrent_file_path, str):
            raise TypeError("Loader takes string as file_path")
        self.torrent_file_path = torrent_file_path
        self.save_directory_path = save_file_path
        _check_file(torrent_file_path)
        source = _read_source_from_file(torrent_file_path)
        self._content = BencodeParser.parse(source)[0]
        BencodeTranslator.print_bencode(self._content)
        self._tracker = TrackerConnection(self)
        self._allocator = Allocator(self, self.get_length(), self.get_piece_length())
        # TODO: правильная длина для файла/каталога
        self.is_working = False
        self._info_hash = None

    def download(self):
        self.is_working = True
        self._tracker.start()

    def get_info_hash(self):
        if self._info_hash is None:
            info = self._content[b"info"]
            info_bencode = BencodeTranslator.translate_to_bencode(info)
            self._info_hash = get_sha_1_hash(info_bencode)
        return self._info_hash

    def get_tracker(self):
        return self._tracker

    def get_length(self):
        return self._content[b'info'][b'length']

    def get_piece_length(self):
        return self._content[b'info'][b'piece length']

    def get_piece_hash(self, piece_index: int):
        return self._content[b'info'][b'pieces'][
               piece_index * 20:piece_index * 20 + 20]

    def get_file_name(self):
        return self._content[b'info'][b'name']

    def get_file_path(self):
        return self.save_directory_path + "\\" + self.get_file_name().decode()