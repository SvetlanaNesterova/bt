from pathlib import Path
from  bencode_parser import BencodeParser

class Loader:
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
        # кодировка ? utf-8 полетела
        # UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc0 in position 825: invalid start byte
        with open(self.torrent_file_path, 'rb') as meta:
            source = meta.read()
            print(source)
            content = BencodeParser.parse(source)
            print(content)

