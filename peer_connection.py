import time
import queue
import threading
import datetime
import downloader
from peer_sender import PeerSender
from peer_receiver import PeerReceiver
from tracker_speaker import TrackerConnection
from pieces_allocator import Allocator
from messages import bytes_to_int, Messages

BITFIELD_TIMEOUT_SEC = 5
KEEPALIVE_TIMEOUT_SEC = 120

# TODO: проверить, что и куда протаскивается из классов
class PeerConnection(threading.Thread):
    def __init__(self, peer_address: tuple, loader: downloader.Loader,
                 tracker: TrackerConnection, allocator: Allocator):
        threading.Thread.__init__(self)
        self.peer_address = peer_address
        self.loader = loader
        self.tracker = tracker  # TODO: отделить пир от трекера;
                                # TODO: сделать контроль за количеством пиров
        self._allocator = allocator
        self._sender = PeerSender(peer_address, loader, self)
        self._socket = self._sender.get_socket()
        self._was_closed = False
        self._receiver = None
        self._response_queue = queue.Queue()
        self._have_message_queue = queue.Queue()

        self._target_piece_index = None
        self._target_begin = 0
        self._storage = None
        self._lock = threading.Lock()

        self.react = self._get_reactions()
        self._state = "start"
        self._received_bitfield = False

        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False
        self.to_send = []

    def _get_reactions(self):
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
        lock = threading.Lock()
        lock.acquire()
        self.tracker.peers_count -= 1
        lock.release()

    def run(self):
        if not self._sender.try_handshake():
            self._delete_peer_from_list()
            print("NO HANDSHAKE")
            return
        print("Good handshake")

        self._receiver = PeerReceiver(self._socket, self)
        self._receiver.start()
        last_keepalive_time = datetime.datetime.now()
        start_time = -1
        while True:
            self._check_input_messages()
            if self._was_closed:
                self._delete_peer_from_list()
                self._socket.close()
                print("CLOSED")
                return

            if self._state == "start":
                self._greet()
                self._state = "wait_bitfield"
                start_time = datetime.datetime.now()
            elif self._state == "wait_bitfield":
                if self._received_bitfield:
                    self._state = "send_request"
                    self._target_piece_index = self._allocator.try_get_target_piece(self)
                    continue
                time_span = (datetime.datetime.now() - start_time)\
                    .total_seconds()
                if time_span > BITFIELD_TIMEOUT_SEC:
                    print("EXEPTION: no bitfield was sent from peer " + str(self)
                          + " " + str(self.peer_address))
                    self.close()
            elif self._state == "send_request" and not self.peer_choking:
                self._sender.send_request(
                    self._target_piece_index, self._target_begin)
                self._state = "wait_piece"

            time_span = (datetime.datetime.now() - last_keepalive_time).total_seconds()
            if time_span > KEEPALIVE_TIMEOUT_SEC:
                self._sender.send_keepalive()
                self._sender.send_interested()
                last_keepalive_time = datetime.datetime.now()

            # TODO: ask for TARGET
            target = self.get_free_target_piece()
            self._sender.send_request(0, 0)

    def _check_input_messages(self):
        while True:
            try:
                message_type, response = self._response_queue.get_nowait()
                print(message_type.encode(), str(len(response)).encode(), response)
                self.react[message_type](response)
            except queue.Empty:
                return

    def _greet(self):
        if not self._allocator.is_bitfield_empty():
            self._sender.send_bitfield()
        self._sender.send_unchoke()
        self._sender.send_interested()

    def send_have_message(self, piece_index: int):
        self._have_message_queue.put(piece_index)

    def close(self):
        print("Close")
        self._was_closed = True

    # TODO: проверка длины сообщения? нужна вроде бы
    # len == 0
    def _react_keepalive(self, response: bytes):
        pass

    # len == 0 ? 4
    def _react_choke(self, response: bytes):
        self.peer_choking = True

    # len == 0
    def _react_unchoke(self, response: bytes):
        self.peer_choking = False

    # len == 0
    def _react_interested(self, response: bytes):
        self.peer_interested = True

    # len == 0
    def _react_not_interested(self, response: bytes):
        self.peer_interested = False

    def _react_have(self, response: bytes):
        self._allocator.add_have_info(bytes_to_int(response[1:5]), self)

    def _react_bitfield(self, response: bytes):
        self._received_bitfield = True
        self._allocator.add_bitfield_info(response[1:], self)

    def _react_request(self, response: bytes):
        if len(response) != 13:
            print("EXCEPTION! len of request peer message is incorrect: " +
                  response.decode())
        piece_index = bytes_to_int(response[1:5])
        begin = bytes_to_int(response[5:9])
        length = bytes_to_int(response[9:13])
        piece = self._allocator.try_get_piece(piece_index, begin, length, self)
        if piece is not None:
            self.to_send.append((piece_index, begin, length))

    def _react_piece(self, response: bytes):
        print(response)
        piece_index = bytes_to_int(response[1:5])
        begin = bytes_to_int(response[5:9])
        piece = response[9:]
        if piece_index == self._target_piece_index:
            self._storage[begin] = piece  # ???
        if self._target_begin == begin:
            self._target_begin = begin + Messages.length
        self._state = "send_request"

    def _react_cancel(self, response: bytes):
        if len(response) != 13:
            print("EXCEPTION! len of cancel peer message is incorrect: " +
                  response.decode())
        piece_index = bytes_to_int(response[1:5])
        begin = bytes_to_int(response[5:9])
        length = bytes_to_int(response[9:13])
        # TODO: что точно надо сделать для отмены отправления?
        for elem in self.to_send:
            if elem == (piece_index, begin, length):
                self.to_send.remove(elem)
                return
