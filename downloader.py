from pathlib import Path

from bencode_parser import BencodeParser
from bencode_translator import BencodeTranslator
from tracker_speaker import TrackerConnection
from pieces_allocator import Allocator
from torrent_meta import TorrentMeta


def _check_file_correctness(file_path: str):
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
    # TODO: у разных пользователей разный id

    def __init__(self, torrent_file_path: str, save_file_path: str):
        """ takes .torrent file """
        if not isinstance(torrent_file_path, str):
            raise TypeError("Loader takes string as file_path")
        self.torrent_file_path = torrent_file_path
        self.save_directory_path = save_file_path
        _check_file_correctness(torrent_file_path)
        source = _read_source_from_file(torrent_file_path)
        content = BencodeParser.parse(source)[0]
        self.torrent = TorrentMeta(content)
        ######
        BencodeTranslator.print_bencode(content)
        self._tracker = TrackerConnection(self)
        self.allocator = Allocator(self.torrent, self.get_root_dir_path())
        # TODO: правильная длина для файла/каталога
        self.is_working = False

    def download(self):
        self.is_working = True
        self._tracker.start()

    def get_tracker(self):
        return self._tracker

    def get_piece_hash(self, piece_index: int):
        #    return self._content[b'info'][b'pieces'][
        #           piece_index * 20:piece_index * 20 + 20]
        return self.torrent.pieces_hashes[piece_index]

    def get_root_dir_path(self):
        return self.save_directory_path + "//"