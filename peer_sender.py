import socket
from messages import Messages, int_to_four_bytes_big_endian


class PeerSender:
    def __init__(self, peer_address, loader, peer_connection):
        self.peer_address = peer_address
        self._client = peer_connection
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handshake_msg = bytes([19]) + b"BitTorrent protocol" + \
            b"\x00" * 8 + loader.get_info_hash() + loader.get_peer_id()

    def _send_with_length_prefix(self, message: bytes):
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
            # TODO: проверить правильность ip и тд
            return True
        except WindowsError as e:
            try:
                self._socket.close()
            except Exception:
                pass
            return False

    # TODO: корректность формы отсылаемых сообщений --- вроде ок
    def send_keepalive(self):
        self._send_with_length_prefix(b"")

    def send_choke(self):
        self._send_with_length_prefix(Messages.choke)

    def send_unchoke(self):
        self._send_with_length_prefix(Messages.unchoke)

    def send_interested(self):
        self._send_with_length_prefix(Messages.interested)

    def send_not_interested(self):
        self._send_with_length_prefix(Messages.not_interested)

    # TODO: когда посылать have
    def send_have(self, piece_index: int):
        message = Messages.have + int_to_four_bytes_big_endian(piece_index)
        self._send_with_length_prefix(message)

    def send_bitfield(self):
        message = Messages.bitfield + self._client._allocator.get_bitfield()
        self._send_with_length_prefix(message)

    # TODO: обработать кусочки неполной длины
    def send_request(self, piece_index: int, begin: int, is_the_last_piece=False):
        message = Messages.request + int_to_four_bytes_big_endian(piece_index) + \
                  int_to_four_bytes_big_endian(begin) + Messages.length
        #print(b"DONE REQUEST " + message)
        self._send_with_length_prefix(message)

    # TODO: может сам извлечет piece?
    def send_piece(self, piece_index: int, begin: int, piece: bytes):
        message = int_to_four_bytes_big_endian(piece_index) + \
                  int_to_four_bytes_big_endian(begin) + piece
        self._send_with_length_prefix(message)

    # TODO: обработать кусочки неполной длины. Выделить общее?
    def send_cancel(self, piece_index: int, begin: int, is_the_last_piece=False):
        message = Messages.cancel + int_to_four_bytes_big_endian(piece_index) + \
                  int_to_four_bytes_big_endian(begin) + Messages.length
        self._send_with_length_prefix(message)

    def get_socket(self):
        return self._socket
