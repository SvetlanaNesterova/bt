import time
import requests
import threading
from random import Random
from socket import *
from bencode import BencodeParser, BencodeTranslator
from peer import PeerConnection
from torrent_info import int_to_four_bytes_big_endian, bytes_to_int


def _parse_peers_ip_and_port(tracker_answer):
    peers = []
    addresses = tracker_answer[b"peers"]
    #TODO: добавить второй вариант
    for i in range(0, len(addresses), 6):
        peer_info = addresses[i:i + 6]
        peer_ip = ".".join(str(byte) for byte in peer_info[:4])
        peer_port = int.from_bytes(peer_info[4:6], byteorder='big')
        peers.append((peer_ip, peer_port))
    return peers


def convert_str_to_pair_address(url):
    temp = url.split(b':')
    port = temp[-1]
    host = url[0: -len(port) - 1].decode()
    return host, int(port)


def _connect_http(tracker_url, params):
    try:
        response = requests.get(tracker_url, params=params)
        try:
            tracker_answer = BencodeParser.parse(response.content)[0]
            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!111 print
            BencodeTranslator.print_bencode(tracker_answer)
            return tracker_answer
        except Exception as e:
            print("EXCEPTION: ", e)
            return None
    except Exception as e:
        print("BAD REQUEST: ", e)
        return None


def _connect_udp(tracker_url, params):
    address = convert_str_to_pair_address(tracker_url)
    address = (address[0][6:], address[1])
    connection_id = _connect(address)
    session_start = time.time()
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    n = 0
    while True:
        if n > 8:
            #########################################################
            print("FAILED connecting with udp (announce)")
            return None    # TODO: прервать
        if time.time() - session_start >= 59:
            connection_id = _connect(address)
            session_start = time.time()
        transaction_id, message = \
            _generate_announce_request(connection_id, params)
        udp_socket.sendto(message, address)
        udp_socket.settimeout(15 * 2 ** n)
        try:
            data, recv_address = udp_socket.recvfrom(1024)
        except Exception as e:
            print(e, "connect", address)
            n += 1
            print("I NOT received data!!!!")
            continue
        recv_transaction_id, action, tracker_answer = \
            _parse_announce_response(data)
        if len(data) < 20 or (len(data) - 20) % 6 != 0 or \
                recv_address != address or action != 1 or \
                recv_transaction_id != transaction_id:
            n += 1
            print("something wrong during announce " + str(address))
            continue
        break
    print("ЕСТЬ ОТВЕТ")
    print(tracker_answer)
    return tracker_answer


def _connect(address):
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    n = 0
    while True:
        if n > 8:
            ###########################################################
            print("FAILED connecting with udp (connect)")
            return None    # TODO: прервать
        transaction_id, message = _generate_connect_request()
        udp_socket.sendto(message, address)
        udp_socket.settimeout(15*2**n)
        try:
            data, recv_address = udp_socket.recvfrom(16) # TODO: достаточная ли проверка длины
        except Exception as e:
            print(e, "connect", address)
            n += 1
            continue
        action, recv_transaction_id, connection_id = \
            _parse_connect_response(data)
        if recv_address != address or action != 0 or \
                recv_transaction_id != transaction_id:
            print("something wrong during connect" + str(address))
            n += 1
            continue
        break
    return connection_id


def _generate_connect_request():
    protocol_id = b"\x00\x00\x04\x17'\x10\x19\x80"
    action = 0
    transaction_id = int_to_four_bytes_big_endian(
        Random().randint(0, 2 ** 31))
    message = protocol_id + \
              int_to_four_bytes_big_endian(action) + \
              transaction_id
    return transaction_id, message


def _parse_connect_response(data):
    action = bytes_to_int(data[0:4])
    recv_transaction_id = data[4:8]
    connection_id = data[8:16]
    return action, recv_transaction_id, connection_id


def _generate_announce_request(connection_id, params):
    action = int_to_four_bytes_big_endian(1)
    transaction_id = int_to_four_bytes_big_endian(
        Random().randint(0, 2 ** 31))
    info_hash = params["info_hash"]
    peer_id = params["peer_id"]

    downloaded = params["downloaded"].to_bytes(8, byteorder='big')
    left = params["left"].to_bytes(8, byteorder='big')
    uploaded = params["uploaded"].to_bytes(8, byteorder='big')

    if "event" in params:
        event = params["event"]
        if event == "completed":
            event = 1
        elif event == "started":
            event = 2
        elif event == "stopped":
            event = 3
    else:
        event = 0
    event = int_to_four_bytes_big_endian(event)
    ip = int_to_four_bytes_big_endian(0)
    key = int_to_four_bytes_big_endian(0)
    if "numwant" in params:
        num_want = params["numwant"]
    else:
        num_want = 50
    num_want = int_to_four_bytes_big_endian(num_want)
    port = params["port"].to_bytes(2, byteorder='big')
    message = connection_id + action + transaction_id + \
              info_hash + peer_id + \
              downloaded + left + uploaded + \
              event + ip + key + num_want + port
    return transaction_id, message


def _parse_announce_response(data):
    action = bytes_to_int(data[0:4])
    transaction_id = data[4:8]
    interval = bytes_to_int(data[8:12])
    peers_addreses = data[20:]
    tracker_answer = {b"interval": interval, b"peers": peers_addreses}
    return transaction_id, action, tracker_answer


class TrackersConnector:
    def __init__(self, loader):
        self.loader = loader
        self.tracker_count = 0
        self.lock = threading.Lock()

    def start(self):
        urls = self.loader.torrent.announce_list
        for tracker_url in urls:
            if tracker_url.startswith(b"udp"):
                TrackerConnection(
                    self, tracker_url, _connect_udp).start()
            elif tracker_url.startswith(b"http"):
                TrackerConnection(
                    self, tracker_url, _connect_http).start()
            self.increase_tracker_count()
        while True:
            time.sleep(15)
            if self.tracker_count == 0:
                print("PANIC!!! Trackers ended.")
                return
            print("У меня все ок")

    def increase_tracker_count(self):
        self.lock.acquire()
        self.tracker_count += 1
        self.lock.release()

    def decrease_tracker_count(self):
        self.lock.acquire()
        self.tracker_count -= 1
        self.lock.release()


class TrackerConnection(threading.Thread):
    def __init__(self, connector: TrackersConnector,
                 tracker_url, connection_method):
        threading.Thread.__init__(self)
        self.loader = connector.loader
        self.connector = connector
        self._tracker_url = tracker_url
        self.peers_count = 0
        self.peers = set()
        self._connect = connection_method
        self.lock = threading.Lock()

    def run(self):
        first_answer = self._try_connect_tracker_first_time()
        if first_answer is None:
            self.connector.decrease_tracker_count()
            return
        peers = _parse_peers_ip_and_port(first_answer)
        self._connect_peers(peers)

        # Hmmm? TODO: правильное отслеживание количества пиров и ведение отчетности
        while self.loader.is_working:
            print("У меня тоже все ок " + self.name)
            time.sleep(5)
            self.lock.acquire()
            print("Current peers number: ", self.peers_count)
            print(self.peers)
            if self.peers_count < 20:
                answer = self._try_connect_tracker_for_more_peers()
                if answer is None:
                    self.connector.decrease_tracker_count()
                    print("ooooo no, tracker go out")
                    return
                peers = _parse_peers_ip_and_port(answer)
                self._connect_peers(peers)
            self.lock.release()
        print('OOOOPS')

    def _try_connect_tracker_first_time(self):
        print("Try " + str(self._tracker_url))
        # ip =
        left = self.loader.allocator.get_left_bytes_count()
        params = {
            "info_hash": self.loader.torrent.info_hash,
            "peer_id": self.loader.get_peer_id(),
            "port": 6889,  # попробовать другие
            "uploaded": 0,
            "downloaded": 0,
            "left": left,
            "event": "started",
        }
        return self._connect(self._tracker_url, params)

    def _try_connect_tracker_for_more_peers(self):
        left = self.loader.allocator.get_left_bytes_count()
        downloaded = self.loader.torrent.length - left
        params = {
            "info_hash": self.loader.torrent.info_hash,
            "peer_id": self.loader.get_peer_id(),
            "port": 6889,  # попробовать другие
            "uploaded": downloaded // 2,  # TODO: скорректировать текущие цифры
            "downloaded": downloaded,
            "left": left,
            "numwant": 50  # TODO: скорректировать
        }
        return self._connect(self._tracker_url, params)

    def _connect_peers(self, peers):
        n = 1
        for peer in peers:
            _thread = PeerConnection(peer, self.loader, self, self.loader.allocator)
            _thread.start()
            self.increase_peers_count(_thread)
            n += 1

    """Exception in thread Thread-57:
    Traceback (most recent call last):
    File "C:/Users\dns\AppData\Local\Programs\Python\Python35-32\lib\threading.py", line 914, in _bootstrap_inner
    self.run()
    File "C:/Users/dns/PycharmProjects/bittorent_client\peer.py", line 69, in run
    self._check_input_messages()
    File "C:/Users/dns/PycharmProjects/bittorent_client\peer.py", line 117, in _check_input_messages
    self.react[message_type](response)
    File "C:/Users/dns/PycharmProjects/bittorent_client\peer.py", line 211, in _react_piece
    self._allocator.save_piece(piece_index, self._storage, self)
    File "C:/Users/dns/PycharmProjects/bittorent_client\pieces_allocator.py", line 107, in save_piece
    for other_peer in self._peers_pieces_info.keys():
    RuntimeError: dictionary changed size during iteration"""

    def increase_peers_count(self, peer):
        #self.lock.acquire()
        self.peers_count += 1
        self.peers.add(peer)
        #self.lock.release()

    def decrease_peers_count(self, peer):
        self.lock.acquire()
        self.peers_count -= 1
        self.peers.remove(peer)
        self.lock.release()