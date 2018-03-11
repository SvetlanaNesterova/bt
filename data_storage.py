import os
import logging
from torrent_info import TorrentMeta, FileRecord

class DataStorage:
    def __init__(self, torrent: TorrentMeta, root_dir_path, logger):
        self.LOG = logging.getLogger(logger.name + ".DataStorage")
        self.torrent = torrent
        self.root_dir = root_dir_path
        self.bytes_count = 0
        for file_record in self.torrent.files:
            if file_record.is_downloading:
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
        self.bytes_count += length
        if not os.path.exists(path):
            with open(path, 'ab') as file:
                self.LOG.info("Creating file with length=%d, piece_len=%d '%s'"
                              % (length, self.torrent.piece_length, path))
                for i in range(length // self.torrent.piece_length):
                    file.write(bytes(self.torrent.piece_length))
                file.write(bytes(length % self.torrent.piece_length))
        file_record.path = path

    """
    def _config_file(self):
        path = Path(self._file_path)
        if not path.exists():
            with open(self._file_path, 'ab') as file:
                for i in range(self.allocator.pieces_count - 1):
                    file.write(bytes(self.allocator.piece_length))
                file.write(bytes(self.allocator.length % self.allocator.piece_length))
    """

    def write_piece(self, piece_index, piece):
        start = piece_index * self.torrent.piece_length
        finish = min((piece_index + 1) * self.torrent.piece_length, self.torrent.length)
        start_in_piece = 0
        written_len = 0
        while start < finish:
            file_rec, offset = self._find_piece_in_files(start)
            len_to_write = min(finish - start, file_rec.length - offset)
            if file_rec.is_downloading:
                path = file_rec.path
                with open(path, 'ab') as file:
                    file.seek(offset)
                    file.write(piece[start_in_piece:start_in_piece + len_to_write])
                written_len += len_to_write
                self.LOG.info("Write piece '%d' on place '%d' in file '%s'"
                              % (piece_index, offset, path))
            start += len_to_write
            start_in_piece += len_to_write
        return written_len

    def read_piece_segment(self, piece_index, begin, length):
        start = piece_index * self.torrent.piece_length + begin
        file_rec, offset = self._find_piece_in_files(start)
        if not file_rec.is_downloading:
            return None
        path = file_rec.path
        with open(path, 'rb') as file:
            file.seek(offset)
            segment = file.read(length)
            return segment

    def _find_piece_in_files(self, start_byte):
        for file_record in self.torrent.files:
            if start_byte < file_record.offset + file_record.length:
                return file_record, start_byte - file_record.offset
