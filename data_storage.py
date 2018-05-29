import os
import mmap
import logging
from torrent_info import TorrentMeta, FileRecord

class DataStorage:
    def __init__(self, torrent: TorrentMeta, root_dir_path, logger):
        self.log = logging.getLogger(logger.name + ".DataStorage")
        self.torrent = torrent
        self.root_dir = root_dir_path
        self.bytes_count = 0
        for file_record in self.torrent.files:
            if file_record.is_downloading:
                self._create_file_structure(file_record)

    def _create_file_structure(self, file_record: FileRecord):
        path = self.root_dir + self.torrent.dir_name.decode()
        for elem in file_record.local_path:
            if not os.path.exists(path):
                os.makedirs(path)
            path += "\\" + elem.decode()
        self._make_file(path, file_record)

    def _make_file(self, path: str, file_record: FileRecord):
        length = file_record.length
        self.bytes_count += length
        if not os.path.exists(path):
            with open(path, 'wb') as file:
                self.log.info("Creating file with length=%d, piece_len=%d '%s'"
                              % (length, self.torrent.piece_length, path))
                for i in range(length // self.torrent.piece_length):
                    file.write(bytes(self.torrent.piece_length))
                file.write(bytes(length % self.torrent.piece_length))
        file_record.path = path

    def write_piece(self, piece_index, piece):
        written_len = 0
        piece_start = piece_index * self.torrent.piece_length
        for file_rec in self.torrent.files:
            if file_rec.pieces_from <= piece_index <= file_rec.pieces_to:
                if file_rec.is_downloading:
                    start = max(piece_start, file_rec.offset)
                    finish = min(piece_start + self.torrent.piece_length,
                                 file_rec.offset + file_rec.length)
                    start_in_piece = start - piece_start
                    finish_in_piece = finish - piece_start
                    fragment = piece[start_in_piece:finish_in_piece]

                    start_in_file = start - file_rec.offset
                    self._write_file_fragment(
                        fragment, start_in_file, file_rec)

                    len_to_write = finish_in_piece - start_in_piece
                    written_len += len_to_write

                    self.log.info("Write piece '%d' on place '%d' in file '%s'"
                                  % (piece_index,
                                     start_in_file,
                                     file_rec.path))
        return written_len

    def _write_file_fragment(self, fragment, offset, file_rec):
        path = file_rec.path
        try:
            with open(path, "r+b") as file:
                map_offset = (offset // mmap.ALLOCATIONGRANULARITY) * \
                             mmap.ALLOCATIONGRANULARITY
                inner_offset = offset % mmap.ALLOCATIONGRANULARITY
                map_len = len(fragment) + inner_offset
                mem_map = mmap.mmap(file.fileno(), map_len, offset=map_offset)
                mem_map[inner_offset:inner_offset+len(fragment)] = fragment
                mem_map.close()
        except Exception as ex:
            print("\n!!! File exception in file '%s': %s" %(path, str(ex)))
            print("!!! It maybe better stop downloading.")
            self.log.fatal("Exception during file saving in file '%s': %s"
                           % (path, str(ex)))

    def read_piece_segment(self, piece_index, begin, length):
        start = piece_index * self.torrent.piece_length + begin
        file_rec, offset = self.find_piece_in_files(start)
        if not file_rec.is_downloading:
            return None
        path = file_rec.path
        with open(path, 'rb') as file:
            file.seek(offset)
            segment = file.read(length)
            return segment

    def find_piece_in_files(self, start_byte):
        for file_record in self.torrent.files:
            if start_byte < file_record.offset + file_record.length:
                return file_record, start_byte - file_record.offset
        return None
