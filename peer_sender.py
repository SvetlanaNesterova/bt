import socket
from messages import Messages, int_to_four_bytes_big_endian


class PeerSender:
    def __init__(self, peer_address, loader):
        self.peer_address = peer_address
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handshake_msg = bytes([19]) + b"BitTorrent protocol" + \
            b"\x00" * 8 + loader.get_info_hash() + loader.get_peer_id()

    def send_with_length_prefix(self, message):
        message = int_to_four_bytes_big_endian(len(message)) + message
        self._socket.send(message)

    def try_handshake(self):
        try:
            self._socket.connect(self.peer_address)
            self._socket.send(self.handshake_msg)
            self._socket.settimeout(3)
            data = self._socket.recv(len(self.handshake_msg))
            self._socket.settimeout(None)
            if not data:
                return False
            if data[:20] != bytes([19]) + b"BitTorrent protocol":
                return False
            return True
        except WindowsError as e:
            try:
                self._socket.close()
            except Exception:
                pass
            return False

    def send_keepalive(self):
        self.send_with_length_prefix(b"")

    def send_choke(self):
        self.send_with_length_prefix(Messages.choke)

    def send_unchoke(self):
        self.send_with_length_prefix(Messages.unchoke)

    def send_interested(self):
        self.send_with_length_prefix(Messages.interested)

    def send_not_interested(self):
        self.send_with_length_prefix(Messages.not_interested)

    def send_have(self, piece_index):
        message = Messages.have + int_to_four_bytes_big_endian(piece_index)
        self.send_with_length_prefix(message)

    def send_bitfield(self):
        raise NotImplementedError

    # TODO: обработать кусочки неполной длины
    def try_send_request(self, piece_index, begin, is_the_last_piece=False):
        message = Messages.request + int_to_four_bytes_big_endian(piece_index) + \
                  int_to_four_bytes_big_endian(begin) + Messages.length
        print("DONE REQUEST")
        self.send_with_length_prefix(message)

    def send_piece(self, piece_index, begin, piece):
        message = int_to_four_bytes_big_endian(piece_index) + \
                  int_to_four_bytes_big_endian(begin) + piece
        self.send_with_length_prefix(message)

    # TODO: обработать кусочки неполной длины. Выделить общее?
    def send_cancel(self, piece_index, begin, is_the_last_piece=False):
        message = Messages.cancel + int_to_four_bytes_big_endian(piece_index) + \
                  int_to_four_bytes_big_endian(begin) + Messages.length
        self.send_with_length_prefix(message)
