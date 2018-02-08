import queue
import threading
import datetime
from peer_sender import PeerSender
from peer_receiver import PeerReceiver
from messages import bytes_to_int, Messages, get_sha_1_hash

BITFIELD_TIMEOUT_SEC = 2
KEEPALIVE_TIMEOUT_SEC = 120


# TODO: проверить, что и куда протаскивается из классов
class PeerConnection(threading.Thread):
    def __init__(self, peer_address: tuple, loader, tracker_connection, allocator):
        threading.Thread.__init__(self)
        self.peer_address = peer_address
        self.loader = loader
        self.tracker = tracker_connection  # TODO: отделить пир от трекера;
                                # TODO: сделать контроль за количеством пиров
        self._allocator = allocator
        self.react = self._get_reactions()
        self._sender = PeerSender(peer_address, loader, self)
        self._socket = self._sender.get_socket()
        self._receiver = None
        self._response_queue = queue.Queue()
        self._have_message_queue = queue.Queue()
        self._was_closed = False

        self._target_piece_index = None
        self._target_begin = 0
        self._target_piece_length = None
        self._target_segment_length = None
        self._storage = b""
        self._state = "start"
        self._received_bitfield = False

        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

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
        self._allocator.remove_peer(self)

    def run(self):
        if not self._sender.try_handshake():
            self._delete_peer_from_list()
            return
        self._receiver = PeerReceiver(self._socket, self)
        self._receiver.start()
        start_time = last_keepalive_time = datetime.datetime.now()
        while True:
            self._check_input_messages()
            self._send_haves()

            if self._was_closed:
                self._delete_peer_from_list()
                self._socket.close()
                print("CLOSED")
                return

            if self._state == "start":
                self._greet()
                self._state = "wait_bitfield"
            elif self._state == "wait_bitfield":
                if self._received_bitfield:
                    self._state = "need_target"
                time_span = (datetime.datetime.now() - start_time).total_seconds()
                if time_span > BITFIELD_TIMEOUT_SEC:
                    print("EXEPTION: no bitfield was sent from peer " + str(self)
                          + " " + str(self.peer_address))
                    self.close()
            elif self._state == "need_target":
                if self._try_get_new_target():
                    self._state = "send_request"
                else:
                    self.close()
                    #break             ???????????????
            elif self._state == "send_request" and not self.peer_choking:
                self._make_request()
                self._state = "wait_piece"

            time_span = (datetime.datetime.now() - last_keepalive_time).total_seconds()
            if time_span > KEEPALIVE_TIMEOUT_SEC:
                self._sender.send_keepalive()
                self._sender.send_interested()
                last_keepalive_time = datetime.datetime.now()

    def _greet(self):
        if not self._allocator.is_bitfield_empty():
            self._sender.send_bitfield()
        self._sender.send_unchoke()
        self._sender.send_interested()

    def _check_input_messages(self):
        while True:
            try:
                message_type, response = self._response_queue.get_nowait()
                self.react[message_type](response)
                #print(message_type.encode() + b" " + response + b"\n")
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
        print("Close")
        self._was_closed = True

    def _try_get_new_target(self):
        target = self._allocator.try_get_target_piece_and_length(self)
        if target:
            self._target_piece_index = target[0]
            self._target_piece_length = target[1]
            self._target_segment_length = min(
                self._target_piece_length,
                Messages.piece_segment_length)
            return  True
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

        piece = self._allocator.try_get_piece_segment(piece_index, begin, length, self)
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
            self._target_segment_length = min(self._target_piece_length - self._target_begin,
                            Messages.piece_segment_length)
            self._state = "send_request"

            if self._target_begin == self._target_piece_length:
                _hash = get_sha_1_hash(self._storage)
                expected_hash = self.loader.get_piece_hash(piece_index)
                if _hash == expected_hash:
                    self._allocator.save_piece(piece_index, self._storage, self)
                    print("SAVED GOOD PIECE!!!!!!" + str(self.peer_address))
                    self._state = "wait_target"
                    return
                else:
                    # Если хэш не совпал
                    pass

    def _react_cancel(self, response: bytes):
        if len(response) != 13:
            print("EXCEPTION! len of cancel peer message is incorrect: " +
                  response.decode())
        piece_index = bytes_to_int(response[1:5])
        begin = bytes_to_int(response[5:9])
        length = bytes_to_int(response[9:13])
        # TODO: что точно надо сделать для отмены отправления? --- А есть ли что отменять?
        #for elem in self.to_send:
        #    if elem == (piece_index, begin, length):
        #        self.to_send.remove(elem)
        #        return
