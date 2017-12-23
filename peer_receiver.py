import threading
from messages import Messages, bytes_to_int


class PeerReceiver(threading.Thread):
    def __init__(self, _socket, connection):
        threading.Thread.__init__(self)
        self._socket = _socket
        self._connection = connection

    def run(self):
        while True:
            response_len = bytes_to_int(self._socket.recv(4))
            if not response_len:
                self._connection.close()
                return

            data = b""
            while response_len > 0:
                received = self._socket.recv(min(1024, response_len))
                if not received:
                    self._connection.close()
                    return
                response_len -= 1024
                data += received
            response = data

            if len(response) == 0:
                message_type = "keepalive"
            elif response[0] > 8:
                print(b"Unknown message type", response[0], response)
                # Выход?
                continue
            else:
                message_type = Messages.messages_types[response[0]]

            self._connection.response_queue.put((message_type, response))
