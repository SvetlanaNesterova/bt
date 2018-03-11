import logging
from threading import Lock
from peer import PeerConnection
from data_storage import DataStorage
from torrent_info import TorrentMeta


class Piece:
    def __init__(self, index: int, is_downloading: bool):
        self.index = index
        self.have = False
        self.count_in_peers = 0
        self.is_downloading = is_downloading
        self.downloader = None


# TODO: наставить блокировочек
class Allocator:
    def __init__(self, torrent: TorrentMeta, root_dir_path: str, logger):
        self.LOG = logging.getLogger(logger.name + ".Allocator")
        self.length = torrent.length
        self.piece_length = torrent.piece_length
        self.pieces_count = self.length // self.piece_length + \
            (1 if self.length % self.piece_length > 0 else 0)
        self._data_storage = DataStorage(torrent, root_dir_path, logger)
        self._left_bytes_count = self._data_storage.bytes_count

        self._pieces = []
        for piece_index in range(self.pieces_count):
            is_downloading = False
            start_byte = piece_index * self.piece_length
            finish_byte = min((piece_index + 1) * self.piece_length, self.length)
            while start_byte < finish_byte:
                file_record, offset = \
                    self._data_storage._find_piece_in_files(start_byte)
                if file_record.is_downloading:
                    is_downloading = True
                start_byte += min(finish_byte - start_byte,
                                  file_record.length - offset)
            self._pieces.append(Piece(piece_index, is_downloading))

        self._peers_pieces_info = dict()
        self._peers_targets = dict()
        bit_size = self.pieces_count // 8 + \
            (1 if self.pieces_count % 8 != 0 else 0)
        self._my_bitfield = bytearray(bit_size)
        self._is_empty = True
        self._lock = Lock()

    def print_state(self):
        with self._lock:
            for piece in self._pieces:
                c = 1 if piece.have else 0
                if piece.downloader is None:
                    print(str(c) + "----", end=" ")
                else:
                    print("%d %4d" % (c, piece.downloader.index), end=" ")

    def get_left_bytes_count(self):
        return self._left_bytes_count

    def is_bitfield_empty(self):
        return self._is_empty

    def get_bitfield(self):
        return self._my_bitfield

    def try_get_target_piece_and_length(self, peer: PeerConnection):
        """
        Вернет False, если у пира не осталось кусочков,
        которых клиент не загрузил. Иначе вернет номер кусочка, который
        нужно загружать у этого пира и длину этого кусочка
        """
        with self._lock:
            if peer not in self._peers_pieces_info.keys():
                self.LOG.error("Not bitfield info about peer " + str(peer))
                return False
            target_piece = self._find_target_piece_with_min_loaders_count(peer)
            if target_piece == -1:
                return False

            prev = self._peers_targets[peer]
            if peer is not None:
                self._pieces[prev].downloader = None
            self._pieces[target_piece].downloader = peer
            self._peers_targets[peer] = target_piece

            if target_piece == self.pieces_count - 1:
                return target_piece, \
                       self.length - (self.pieces_count - 1) * self.piece_length
            else:
                return target_piece, self.piece_length


    def _find_target_piece_with_min_loaders_count(self, peer):
        peer_have = self._peers_pieces_info[peer]
        minimal_count = 1000
        target_piece = -1
        for index in range(self.pieces_count):
            if peer_have[index] and not self._pieces[index].have and \
                    self._pieces[index].is_downloading and \
                            self._pieces[index].downloader is None:
                if self._pieces[index].count_in_peers < minimal_count:
                    minimal_count = self._pieces[index].count_in_peers
                    target_piece = index

        # if target_piece = -1: TODO: мб дублирующая загрузка

        return target_piece

    def add_bitfield_info(self, bitfield: bytes, peer: PeerConnection):
        with self._lock:
            if peer in self._peers_pieces_info.keys():
                self.LOG.error("Repeat bitfield adding by peer " + str(peer))
                return
            if len(bitfield) != len(self._my_bitfield):
                self.LOG.error("Incorrect bitfield len by peer " + str(peer))
                return
            pieces_info = [False] * self.pieces_count
            index = 0

            for byte in bitfield:
                value = byte
                for i in range(8):
                    value >>= 1
                    if value & 1 == 1:
                        pieces_info[index] = True
                        self._pieces[index].count_in_peers += 1
                    index += 1
                    if index == self.pieces_count:
                        break
                if index == self.pieces_count:
                    break
            self._peers_pieces_info[peer] = pieces_info
            self._peers_targets[peer] = None

    def add_have_info(self, piece_index: int, peer: PeerConnection):
        with self._lock:
            if peer not in self._peers_pieces_info.keys():
                self._peers_pieces_info[peer] = [False] * self.pieces_count
            self._peers_pieces_info[peer][piece_index] = True
            self._pieces[piece_index].count_in_peers += 1

    def save_piece(self, piece_index: int, piece: bytes,
                   peer: PeerConnection):
        with self._lock:
            if self._pieces[piece_index].have:
                return
            self._pieces[piece_index].have = True
            written_len = self._data_storage.write_piece(piece_index, piece)
            self._left_bytes_count -= written_len
            self._mark_my_bitfield(piece_index)
            self._is_empty = False
            for other_peer in self._peers_pieces_info.keys():
                if other_peer != peer:
                    other_peer.send_have_message(piece_index)
            if self._left_bytes_count == 0:
                print("DOWNLOADING FINISHED")
                self.LOG.info("DOWNLOADING FINISHED")
                # TODO: полная загрузка

    def _mark_my_bitfield(self, piece_index):
         self._my_bitfield[piece_index // 8] |= (1 << (piece_index % 8))

    def try_get_piece_segment(self, piece_index: int, begin: int, length: int,
                              peer: PeerConnection):
        with self._lock:
            piece = self._pieces[piece_index]
            if piece.have:
                return self._data_storage.read_piece_segment(
                    piece_index, begin, length)
            else:
                return False

    def remove_peer(self, peer: PeerConnection):
        with self._lock:
            if peer not in self._peers_pieces_info.keys():
                return
            piece_info = self._peers_pieces_info[peer]
            for index in range(len(piece_info)):
                if piece_info[index]:
                    self._pieces[index].count_in_peers -= 1
            self._peers_pieces_info.pop(peer)
            target = self._peers_targets[peer]
            if target is not None:
                self._pieces[target].downloader = None
            self._peers_targets.pop(peer)