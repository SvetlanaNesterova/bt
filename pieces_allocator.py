from peer_connection import PeerConnection
from data_storage import DataStorage
from torrent_meta import TorrentMeta

class Piece:
    def __init__(self, index: int):
        self.index = index
        self.have = False
        self.count_in_peers = 0
        self.downloader = None


# TODO: наставить блокировочек
class Allocator:
    def __init__(self, torrent: TorrentMeta, root_dir_path: str):
        self.length = torrent.length
        self.piece_length = torrent.piece_length
        self.pieces_count = self.length // self.piece_length + \
            (1 if self.length % self.piece_length > 0 else 1)
        self._pieces = [Piece(i) for i in range(self.pieces_count)]
        self._peers_pieces_info = dict()
        bit_size = self.pieces_count // 8 + \
            (1 if self.pieces_count % 8 != 0 else 0)
        self._my_bitfield = bytearray(bit_size)
        self._is_empty = True
        self._left_bytes_count = self.length
        self._data_storage = DataStorage(torrent, root_dir_path)

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
        if peer not in self._peers_pieces_info.keys():
            raise Exception ("Not bitfield info about peer " + str(peer))
        target_piece = self._find_target_piece_with_min_loaders_count(peer)
        self._pieces[target_piece].downloader = peer
        if target_piece == -1:
            return False
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
                            self._pieces[index].downloader is None:
                if self._pieces[index].count_in_peers < minimal_count:
                    minimal_count = self._pieces[index].count_in_peers
                    target_piece = index
        return target_piece

    def add_bitfield_info(self, bitfield: bytes, peer: PeerConnection):
        if peer in self._peers_pieces_info.keys():
            print("EXCEPTION: repeat bitfield adding by peer " + str(peer))
            return
        if len(bitfield) != len(self._my_bitfield):
            print("EXCEPTION: incorrect bitfield len")
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

    def add_have_info(self, piece_index: int, peer: PeerConnection):
        if peer not in self._peers_pieces_info.keys():
            self._peers_pieces_info[peer] = [False] * self.pieces_count
        self._peers_pieces_info[peer][piece_index] = True
        self._pieces[piece_index].count_in_peers += 1

    def save_piece(self, piece_index: int, piece: bytes,
                   peer: PeerConnection):
        if self._pieces[piece_index].have:
            return
        self._pieces[piece_index].have = True
        self._data_storage.write_piece(piece_index, piece)
        self._left_bytes_count -= len(piece)
        self._mark_my_bitfield(piece_index)
        self._is_empty = False
        for other_peer in self._peers_pieces_info.keys():
            if other_peer != peer:
                other_peer.send_have_message(piece_index)
        if self._left_bytes_count == 0:
            pass
            # ЗАГРУЗКА ЗАКОНЧЕНА
            # TODO: полная загрузка

    def _mark_my_bitfield(self, piece_index):
        self._my_bitfield[piece_index // 8] |= (1 << (piece_index % 8))

    def try_get_piece_segment(self, piece_index: int, begin: int, length: int,
                              peer: PeerConnection):
        piece = self._pieces[piece_index]
        if piece.have:
            return self._data_storage.read_piece_segment(
                piece_index, begin, length)
        else:
            return False

    def remove_peer(self, peer: PeerConnection):
        if peer not in self._peers_pieces_info.keys():
            return
        piece_info = self._peers_pieces_info[peer]
        for index in range(len(piece_info)):
            if piece_info[index]:
                self._pieces[index].count_in_peers -= 1
        self._peers_pieces_info.pop(peer)
