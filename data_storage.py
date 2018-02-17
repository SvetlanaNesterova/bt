import os
from pathlib import Path
from torrent_info import TorrentMeta, FileRecord

class DataStorage:
    def __init__(self, torrent, root_dir_path):
        self.torrent = torrent
        self.root_dir = root_dir_path
        for file_record in self.torrent.files:
            self._create_file_structure(file_record)

    def _create_file_structure(self, file_record: FileRecord):
        path = self.root_dir + self.torrent.dir_name.decode()
        for elem in file_record.path:
            if not os.path.exists(path):
                os.makedirs(path)
            path += "\\" + elem.decode()
        self._make_file(path, file_record)

    def _make_file(self, path: str, file_record: FileRecord):
        length = file_record.length
        if not os.path.exists(path):
            with open(path, 'ab') as file:
                print(path, length, self.torrent.piece_length)
                for i in range(length // self.torrent.piece_length):
                    file.write(bytes(self.torrent.piece_length))
                file.write(bytes(length % self.torrent.piece_length))
        file_record.path = path

    def _config_file(self):
        path = Path(self._file_path)
        if not path.exists():
            with open(self._file_path, 'ab') as file:
                for i in range(self.allocator.pieces_count - 1):
                    file.write(bytes(self.allocator.piece_length))
                file.write(bytes(self.allocator.length % self.allocator.piece_length))

    def write_piece(self, piece_index, piece):
        start = piece_index * self.torrent.piece_length
        path, offset = self._find_piece_in_files(start)
        with open(path, 'ab') as file:
            file.seek(offset)
            file.write(piece)

    def read_piece_segment(self, piece_index, begin, length):
        start = piece_index * self.torrent.piece_length + begin
        path, offset = self._find_piece_in_files(start)
        with open(path, 'rb') as file:
            file.seek(offset)
            segment = file.read(length)
            return segment

    def _find_piece_in_files(self, start_byte):
        for file_record in self.torrent.files:
            if start_byte < file_record.offset + file_record.length:
                return file_record.path, start_byte - file_record.offset
