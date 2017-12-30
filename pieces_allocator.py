from peer_connection import PeerConnection


class Piece:
    def __init__(self, index: int):
        self.index = index
        self.have = False
        self.saved_piece = None
        self.count_in_peers = 0
        self.downloader = None


class Allocator:
    def __init__(self, loader, length: int, piece_length: int):
        pieces_count = length // piece_length + (1 if length % piece_length > 0 else 1)
        self._loader = loader
        self.real_pieces_count = pieces_count
        size = pieces_count // 8 + (1 if pieces_count % 8 != 0 else 0)
        self.bitfield_pieces_count = size * 8
        self._my_bitfield = bytes(size)
        self._is_empty = True
        self._pieces = [Piece(i) for i in range(self.bitfield_pieces_count)]
        self._peers_pieces_info = dict()

    def is_bitfield_empty(self):
        return self._is_empty

    def get_bitfield(self):
        return self._my_bitfield

    def try_get_target_piece(self, peer: PeerConnection):
        if not peer in self._peers_pieces_info.keys():
            print("EXCEPTION: not bitfield info about peer " + str(peer))
            return False
        pieces_info = self._peers_pieces_info[peer]
        minimal_count = 1000
        target_piece = -1
        for index in range(len(pieces_info)):
            if pieces_info[index] and not self._pieces[index].have and \
                            self._pieces[index].downloader is None:
                if self._pieces[index].count_in_peers < minimal_count:
                    minimal_count = self._pieces[index].count_in_peers
                    target_piece = index
        self._pieces[target_piece].downloader = peer
        return target_piece

    def add_bitfield_info(self, bitfield: bytes, peer: PeerConnection):
        if peer in self._peers_pieces_info.keys():
            print("EXCEPTION: repeat bitfield adding by peer " + str(peer))
            return
        if len(bitfield) != len(self._my_bitfield):
            print("EXCEPTION: incorrect bitfield len")
            return
        pieces_info = [False] * self.bitfield_pieces_count  #  TODO: корректный размер, взять из info-словаря
        index = 0
        for byte in bitfield:
            value = byte
            for i in range(8):
                value >>= 1
                if value & 1 == 1:
                    try:
                        pieces_info[index] = True
                        self._pieces[index].count_in_peers += 1
                    except Exception as e:
                        print(e)
                        print(len(pieces_info))
                        print(len(self._pieces))
                        print(len(bitfield))
                        raise e
                index += 1
        self._peers_pieces_info[peer] = pieces_info

    def add_have_info(self, piece_index: int, peer: PeerConnection):
        if peer not in self._peers_pieces_info.keys():
            self._peers_pieces_info[peer] = [False] * (len(self._my_bitfield) * 8)  # TODO: корректный размер, взять из info-словаря

        self._peers_pieces_info[peer][piece_index] = True
        self._pieces[piece_index].count_in_peers += 1

    def save_piece(self, piece_index: int, piece: bytes,
                   peer: PeerConnection):
        # TODO: полная загрузка кусочка (по количеству)
        self._pieces[piece_index].have = True
        self._pieces[piece_index].saved_piece = piece
        self._my_bitfield[piece_index // 8] |= (1 << (piece_index % 8))
        self._is_empty = False

    def try_get_piece(self, piece_index: int, begin: int, length: int,
                      peer: PeerConnection):
        piece = self._pieces[piece_index]
        if piece.have:
            return piece.saved_piece[begin:begin + length]
        else:
            return False

    def remove_peer(self, peer: PeerConnection):
        piece_info = self._peers_pieces_info[peer]
        for index in range(len(piece_info)):
            if piece_info[index]:
                self._pieces[index].count_in_peers -= 1
        self._peers_pieces_info.pop(peer)
