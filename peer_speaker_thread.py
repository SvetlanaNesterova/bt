import time
import queue
import threading
from downloader import Loader
from peer_sender import PeerSender
from peer_receiver import PeerReceiver
from tracker_speaker import TrackerConnection
from pieces_allocator import Allocator
from messages import bytes_to_int


# TODO: проверить, что и куда протаскивается из классов
class PeerConnection(threading.Thread):
    def __init__(self, peer_address: tuple, loader: Loader,
                 tracker: TrackerConnection, allocator: Allocator):
        threading.Thread.__init__(self)
        self.peer_address = peer_address
        self.loader = loader
        self.tracker = tracker  # TODO: отделить пир от трекера;
                                # TODO: сделать контроль за количеством пиров
        self.allocator = allocator
        self._sender = PeerSender(peer_address, loader, self)
        self._socket = self._sender.get_socket()
        self._was_closed = False
        self._receiver = None
        self.response_queue = None
        self._state = 'wait'
        self._target_piece_index = None
        self._storage = None

        self.react = self._get_reactions()

        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False
        self.to_send = None

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

        self.response_queue = queue.Queue()
        self._receiver = PeerReceiver(self._socket, self)
        self._receiver.start()
        while True:
            self._check_input_messages()
            if self._was_closed:
                self._delete_peer_from_list()
                self._socket.close()
                print("CLOSED")
                return
            # TODO: ask for TARGET
            time.sleep(2)
            target = self.get_free_target_piece()
            self._sender.send_request(0, 0)

    def _check_input_messages(self):
        while True:
            try:
                message_type, response = self.response_queue.get_nowait()
                print(message_type.encode(), str(len(response)).encode(), response)
                self.react[message_type](response)
            except queue.Empty:
                return

    def get_free_target_piece(self):
        lock = threading.Lock()
        lock.acquire()
        target = None
        for piece in self._states:
            if piece.state == "no":
                piece.state = "loading"
                target = piece
                break
        lock.release()
        return target

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
        self.allocator.add_have_info(bytes_to_int(response[1:5]), self)

    def _react_bitfield(self, response: bytes):
        self.allocator.add_bitfield_info(response[1:], self)

    def _react_request(self, response: bytes):
        if len(response) != 13:
            print("EXCEPTION! len of request peer message is incorrect: " +
                  response)
        piece_index = bytes_to_int(response[1:5])
        begin = bytes_to_int(response[5:9])
        length = bytes_to_int(response[9:13])
        piece = self.allocator.try_get_piece(piece_index, begin, length)
        if piece is not None:
            self.to_send = (piece_index, begin, length)
        # TODO: проверить, не затирается ли предыдущее

    def _react_piece(self, response: bytes):
        print(response)
        piece_index = bytes_to_int(response[1:5])
        begin = bytes_to_int(response[5:9])
        piece = response[9:]
        if piece_index == self._target_piece_index:
            self._storage[begin] = piece  # ???

    def _react_cancel(self, response: bytes):
        if len(response) != 13:
            print("EXCEPTION! len of cancel peer message is incorrect: " +
                  response)
        piece_index = bytes_to_int(response[1:5])
        begin = bytes_to_int(response[5:9])
        length = bytes_to_int(response[9:13])
        piece = self.allocator.try_get_piece(piece_index, begin, length)
        if self.to_send == (piece_index, begin, length):
            # TODO: что точно надо сделать для отмены отправления?
            self.to_send = None


