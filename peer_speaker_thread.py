import time
import queue
import threading
from peer_sender import PeerSender
from peer_receiver import PeerReceiver

# TODO: проверить, что и куда протаскивается из классов


class PeerConnection(threading.Thread):
    def __init__(self, peer_address, loader, tracker, states):
        threading.Thread.__init__(self)
        self.peer = peer_address
        self.loader = loader
        self.tracker = tracker
        self._states = states
        self.sender = PeerSender(peer_address, loader)
        self._socket = self.sender._socket
        self._was_closed = False
        self._receiver = None
        self.response_queue = None

        do = dict()
        do['keepalive'] = self._answer_keepalive
        do['choke'] = self._answer_choke
        do['unchoke'] = self._answer_unchoke
        do['interested'] = self._answer_interested
        do['not_interested'] = self._answer_not_interested
        do['have'] = self._answer_have
        do['bitfield'] = self._answer_bitfield
        do['request'] = self._answer_request
        do['piece'] = self._answer_piece
        do['cancel'] = self._answer_cancel
        self.react = do

    def _delete_peer_from_list(self):
        lock = threading.Lock()
        lock.acquire()
        self.tracker.peers_count -= 1
        lock.release()

    def run(self):
        if not self.sender.try_handshake():
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
            self.sender.try_send_request(0, 0)

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

    def _answer_keepalive(self, response):
        pass

    def _answer_choke(self, response):
        pass

    def _answer_unchoke(self, response):
        pass

    def _answer_interested(self, response):
        pass

    def _answer_not_interested(self, response):
        pass

    def _answer_have(self, response):
        pass

    def _answer_bitfield(self, response):
        pass

    def _answer_request(self, response):
        pass

    def _answer_piece(self, response):
        print(response)

    def _answer_cancel(self, response):
        pass



