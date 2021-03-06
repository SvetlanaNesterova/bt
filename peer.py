import queue
import threading
import socket
import logging
import time
import traceback
from torrent_info import bytes_to_int, int_to_four_bytes_big_endian,\
    Messages, get_sha_1_hash

BITFIELD_TIMEOUT_SEC = 2
KEEPALIVE_TIMEOUT_SEC = 120


class PeerConnection(threading.Thread):
    count = 0
    lock = threading.Lock()

    @staticmethod
    def get_logger(tracker):
        with PeerConnection.lock:
            PeerConnection.count += 1
            logger_name = tracker.log.name + ".PeerConnection." + \
                          str(PeerConnection.count)
            return (PeerConnection.count, logging.getLogger(logger_name))

    def __init__(self, peer_address: tuple, loader, tracker, allocator):
        threading.Thread.__init__(self)
        self.index, self.log = PeerConnection.get_logger(tracker)
        self.peer_address = peer_address
        self._loader = loader
        self._tracker = tracker
        self.allocator = allocator
        self.react = self._set_reactions()
        self._sender = PeerSender(peer_address, loader, self)
        self._socket = self._sender.get_socket()
        self._receiver = None
        self._receiver_closed = True
        self.response_queue = queue.Queue()
        self._have_message_queue = queue.Queue()
        self._was_closed = False
        self._saved_piece = False

        self._target_piece_index = None
        self._target_begin = 0
        self._target_piece_length = None
        self._target_segment_length = None
        self._storage = b""
        self._state = "start"
        self._received_bitfield = False
        self._bitfield = None

        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

    def _set_reactions(self):
        reactions = dict()
        reactions['keepalive'] = self._react_keepalive
        reactions['choke'] = self._react_choke
        reactions['unchoke'] = self._react_unchoke
        reactions['interested'] = self._react_interested
        reactions['not_interested'] = self._react_not_interested
        reactions['have'] = self._react_have
        reactions['bitfield'] = self._react_bitfield
        reactions['request'] = self._react_request
        reactions['piece'] = self._react_piece
        reactions['cancel'] = self._react_cancel
        return reactions

    def _delete_peer_from_list(self):
        self._tracker.connector.delete_peer(self)
        self.allocator.remove_peer(self)

    def run(self):
        if not self._sender.try_handshake():
            self._delete_peer_from_list()
            return
        self._start_receiver()
        start_time = last_keepalive_time = time.time()
        while True:
            if self._receiver_closed:
                self._finish_when_receiver_close()
                return
            if self._was_closed:
                self._finish_when_close_itself()
                return
            self._check_input_messages()
            self._send_haves()
            if self._state == "start":
                self._greet()
                self._state = "wait_bitfield"
            elif self._state == "wait_bitfield":
                if self._received_bitfield:
                    self._state = "need_target"
                time_span = time.time() - start_time
                if time_span > BITFIELD_TIMEOUT_SEC:
                    self.log.error("Exception: no bitfield was sent from '%s'"
                                   % str(self.peer_address))
                    self.close()
                    continue
            elif self._state == "need_target":
                if self._try_get_new_target():
                    self._state = "send_request"
                else:
                    self.log.error("No target for me" + str(self.peer_address))
                    self.close()
                    continue
            elif self._state == "send_request" and not self.peer_choking:
                self._make_request()
                self._state = "wait_piece"

            time_span = time.time() - last_keepalive_time
            if time_span > KEEPALIVE_TIMEOUT_SEC:
                self._sender.send_keepalive()
                self._sender.send_interested()
                last_keepalive_time = time.time()

    def _start_receiver(self):
        self._receiver = PeerReceiver(self._socket, self)
        self._receiver_closed = False
        self._receiver.start()

    def _greet(self):
        if not self.allocator.is_bitfield_empty():
            self._sender.send_bitfield()
        self._sender.send_unchoke()
        self._sender.send_interested()

    def _check_input_messages(self):
        while True:
            try:
                message_type, response = self.response_queue.get_nowait()
                self.react[message_type](response)
            except queue.Empty:
                return

    def _send_haves(self):
        while True:
            try:
                piece_index = self._have_message_queue.get_nowait()
                self._sender.send_have(piece_index)
            except queue.Empty:
                return

    def send_have_message(self, piece_index: int):
        self._have_message_queue.put(piece_index)

    def close(self):
        self._was_closed = True

    def react_receiver_closing(self):
        self._receiver_closed = True

    def _finish_when_receiver_close(self):
        self._delete_peer_from_list()
        self._socket.close()
        self.log.fatal("Connection with peer '%s' was closed "
                       "(receiver closed)" % str(self.peer_address))
        if self._saved_piece:
            new_peer = PeerConnection(self.peer_address, self._loader,
                                      self._tracker, self._loader.allocator)
            new_peer.start()
            self._tracker.connector.add_peer(new_peer)

    def _finish_when_close_itself(self):
        self._delete_peer_from_list()
        self._receiver.react_connection_closed()
        self.log.fatal("Connection with peer '%s' was closed"
                       % str(self.peer_address))

    def _try_get_new_target(self):
        target = self.allocator.try_get_target_piece_and_length(self)
        if target:
            self._target_piece_index = target[0]
            self._target_piece_length = target[1]
            self._target_segment_length = min(
                self._target_piece_length,
                Messages.piece_segment_length)
            return True
        return False

    def _make_request(self):
        self._sender.send_request(
            self._target_piece_index,
            self._target_begin,
            self._target_segment_length)

    # TODO: проверка длины сообщения? нужна вроде бы
    def _react_keepalive(self, response: bytes):
        pass

    def _react_choke(self, response: bytes):
        self.peer_choking = True

    def _react_unchoke(self, response: bytes):
        self.peer_choking = False

    def _react_interested(self, response: bytes):
        self.peer_interested = True

    def _react_not_interested(self, response: bytes):
        self.peer_interested = False

    def _react_have(self, response: bytes):
        self.allocator.add_have_info(bytes_to_int(response[1:5]), self)

    def _react_bitfield(self, response: bytes):
        self._received_bitfield = True
        self._bitfield = response[1:]
        self.allocator.add_bitfield_info(response[1:], self)

    def _react_request(self, response: bytes):
        if len(response) != 13:
            self.log.error("EXCEPTION! len of request peer message is "
                           "incorrect: " + response.decode())

        piece_index = bytes_to_int(response[1:5])
        begin = bytes_to_int(response[5:9])
        length = bytes_to_int(response[9:13])

        piece = self.allocator.try_get_piece_segment(
            piece_index, begin, length)
        # TODO: сделать очередь
        if piece:
            self._sender.send_piece(piece_index, begin, piece)

    def _react_piece(self, response: bytes):
        piece_index = bytes_to_int(response[1:5])
        begin = bytes_to_int(response[5:9])
        piece = response[9:]

        if piece_index == self._target_piece_index and \
                self._target_begin == begin and \
                self._target_segment_length == len(piece):

            self._storage += piece
            self._target_begin = begin + self._target_segment_length
            self._target_segment_length = min(
                self._target_piece_length - self._target_begin,
                Messages.piece_segment_length)
            self._state = "send_request"

            if self._target_begin == self._target_piece_length:
                _hash = get_sha_1_hash(self._storage)
                expected_hash = self._loader.get_piece_hash(piece_index)
                if _hash == expected_hash:
                    self.log.info("SAVED GOOD PIECE from '%s'"
                                  % str(self.peer_address))
                    self.allocator.save_piece(
                        piece_index, self._storage, self)
                    self._saved_piece = True
                    self._state = "need_target"
                    return
                else:
                    self.log.info("Piece with wrong hash from '%s'"
                                  % str(self.peer_address))
                    self._state = "need_target"

    def _react_cancel(self, response: bytes):
        if len(response) != 13:
            self.log.error("EXCEPTION! len of cancel peer message "
                           "is incorrect: " + response.decode())


class PeerSender:
    def __init__(self, peer_address, loader, peer_connection):
        self.peer_address = peer_address
        self._client = peer_connection
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handshake_msg = bytes([19]) + b"BitTorrent protocol" + \
            b"\x00" * 8 + loader.torrent.info_hash + loader.get_peer_id()

    def _send_with_length_prefix(self, message: bytes):
        message = int_to_four_bytes_big_endian(len(message)) + message
        try:
            self._socket.send(message)
        except Exception as ex:
            self._client.log.error("Exception during sending: " + str(ex))
            self._client.close()

    def try_handshake(self):
        try:
            self._socket.connect(self.peer_address)
            self._socket.send(self.handshake_msg)
            self._socket.settimeout(15)
            data = self._socket.recv(len(self.handshake_msg))
            self._socket.settimeout(None)
            if not data:
                return False
            if data[:20] != bytes([19]) + b"BitTorrent protocol":
                return False
            # TODO: проверить правильность ip и тд
            return True
        except WindowsError as ex:
            if ex.errno != 10060 and ex.errno != 10061:
                self._client.log.error(
                    "Exception during sending handsnake " + str(ex))
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
        message = Messages.bitfield + self._client.allocator.get_bitfield()
        self._send_with_length_prefix(message)

    # TODO: обработать кусочки неполной длины
    def send_request(self, piece_index: int, begin: int, length: int):
        message = Messages.request + \
                  int_to_four_bytes_big_endian(piece_index) + \
                  int_to_four_bytes_big_endian(begin) + \
                  int_to_four_bytes_big_endian(length)
        self._send_with_length_prefix(message)

    # TODO: может сам извлечет piece?
    def send_piece(self, piece_index: int, begin: int, piece: bytes):
        message = int_to_four_bytes_big_endian(piece_index) + \
                  int_to_four_bytes_big_endian(begin) + piece
        self._send_with_length_prefix(message)

    # TODO: обработать кусочки неполной длины. Выделить общее?
    def send_cancel(self, piece_index: int, begin: int, length: int):
        message = Messages.cancel + \
                  int_to_four_bytes_big_endian(piece_index) + \
                  int_to_four_bytes_big_endian(begin) + \
                  int_to_four_bytes_big_endian(length)
        self._send_with_length_prefix(message)

    def get_socket(self):
        return self._socket


class PeerReceiver(threading.Thread):
    def __init__(self, _socket, connection: PeerConnection):
        threading.Thread.__init__(self)
        self.log = logging.getLogger(connection.log.name + ".Receiver")
        self._socket = _socket
        self._connection = connection
        self._was_closed = False
        self._connection_closed = False

    def run(self):
        while True:
            if self._connection_closed:
                self._socket.close()
                self.log.fatal("Receiver from peer closed (connection closed)")
                return
            if self._was_closed:
                self._connection.react_receiver_closing()
                self.log.fatal("Receiver from peer closed")
                return
            try:
                response = self._socket.recv(4)
            except Exception as ex:
                self.log.error("Exception during receiving data: '%s' \n%s"
                               % (ex, traceback.format_exc()))
                self.close()
                continue
            if not response:
                self.log.warning("Len-Response was None")
                self.close()
                continue
            response_len = bytes_to_int(response)
            if response_len == 0:
                self.log.warning("Message with zero length was received")

            response = b""
            while response_len > 0:
                try:
                    received = self._socket.recv(min(1024, response_len))
                except Exception as ex:
                    self.log.error("Exception during receiving data: '%s' \n%s"
                                   % (ex, traceback.format_exc()))
                    self.close()
                    break
                if not received:
                    self.log.warning(
                        "No message was received but it was expected")
                    self.close()
                    break
                response_len -= len(received)
                response += received
            else:
                if not response:
                    message_type = "keepalive"
                elif response[0] > 8:
                    self.log.warning("Unknown message type '%d' in '%s'"
                                     % (response[0], response.decode()))
                    continue
                else:
                    message_type = Messages.messages_types[response[0]]
                if not self._connection_closed:
                    self._connection.response_queue.put(
                        (message_type, response))

    def close(self):
        self._was_closed = True

    def react_connection_closed(self):
        self._connection_closed = True
