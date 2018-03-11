import time
import requests
import threading
import logging
import traceback
from random import Random
from socket import *
from bencode import BencodeParser, BencodeTranslator
from peer import PeerConnection
from torrent_info import int_to_four_bytes_big_endian, bytes_to_int

MIN_PEERS_COUNT = 30
FIRST_NUMWANT = 50
NUMWANT = 50  # TODO: скорректировать


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
    port = temp[-1].split(b'/')[0]
    host = url[0: -len(port) - 1].decode()
    return host, int(port)


def _connect_http(tracker_url, params, logger: logging.Logger):
    try:
        response = requests.get(tracker_url, params=params)
        try:
            tracker_answer = BencodeParser.parse(response.content)[0]
            logger.info("Get peers from HTTP tracker '%s'"
                        % tracker_url.decode())
            return tracker_answer
        except Exception as ex:
            logger.error("Exception during parsing tracker '%s' answer: %s\n %s"
                         % (tracker_url.decode(), str(ex), response.content))
            return None
    except Exception as ex:
        logger.error("Exception during HTTP connection with tracker '%s':"
                     "\n %s"
                     % (tracker_url.decode(), str(ex)))
        return None


def _connect_udp(tracker_url, params, logger: logging.Logger):
    logger.info("Try connecting UDP with tracker '%s'" % tracker_url.decode())
    try:
        address = convert_str_to_pair_address(tracker_url)
    except Exception as ex:
        logger.error("Exception during pasring address '%s': %s"
                     % (tracker_url.decode(), str(ex)))
        return
    address = (address[0][6:], address[1])
    connection_id = _connect(address, logger)
    session_start = time.time()
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    n = 0
    while True:
        if n > 8:
            logger.error("Failed connecting UDP with tracker '%s' "
                         "during announce: timeout"
                         % tracker_url.decode())
            return None    # TODO: прервать
        if time.time() - session_start >= 59:
            connection_id = _connect(address, logger)
            session_start = time.time()
        transaction_id, message = \
            _generate_announce_request(connection_id, params)
        udp_socket.sendto(message, address)
        udp_socket.settimeout(15 * 2 ** n)
        try:
            data, recv_address = udp_socket.recvfrom(1024) #TODO: какое поведение при отсутствии ответа?
        except Exception as ex:
            logger.error("Exception during getting UDP response in announce "
                         "with Tracker '%s': '%s'"
                         % (tracker_url.decode(), str(ex)))
            n += 1
            continue
        recv_transaction_id, action, tracker_answer = \
            _parse_announce_response(data)
        if len(data) < 20 or (len(data) - 20) % 6 != 0 or \
                recv_address != address or action != 1 or \
                recv_transaction_id != transaction_id:
            n += 1
            logger.info("Incorrect UDP response in announce "
                        "with Tracker '%s'" % tracker_url.decode())
            continue
        break
    logger.info("Get peers from UDP tracker '%s'" % tracker_url.decode())
    return tracker_answer


def _connect(address, logger: logging.Logger):
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    n = 0
    while True:
        if n > 8:
            logger.error("Failed connecting UDP with tracker '%s' "
                         "during connect: timeout"
                         % str(address))
            return None    # TODO: прервать
        transaction_id, message = _generate_connect_request()
        try:
            udp_socket.sendto(message, address)
        except gaierror as ex:
            logger.error("Exception sending UDP connect to tracker '%s': '%s'"
                         % (str(address), str(ex)))
        udp_socket.settimeout(15*2**n)
        try:
            data, recv_address = udp_socket.recvfrom(16)  # TODO: достаточная ли проверка длины
        except Exception as ex:
            logger.error("Exception during getting UDP response in connect "
                         "with Tracker '%s': '%s'"
                         % (str(address), str(ex)))
            n += 1
            continue
        action, recv_transaction_id, connection_id = \
            _parse_connect_response(data)
        if recv_address != address or action != 0 or \
                recv_transaction_id != transaction_id:
            logger.info("Incorrect UDP response in connect "
                        "with Tracker '%s'" % str(address))
            continue
        break
    return connection_id


def _generate_connect_request():
    protocol_id = b"\x00\x00\x04\x17'\x10\x19\x80"
    action = int_to_four_bytes_big_endian(0)
    transaction_id = int_to_four_bytes_big_endian(
        Random().randint(0, 2 ** 31))
    message = protocol_id + action + transaction_id
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
    peers_addresses = data[20:]
    tracker_answer = {b"interval": interval, b"peers": peers_addresses}
    return transaction_id, action, tracker_answer


class TrackersConnector:
    def __init__(self, loader):
        self.LOG = logging.getLogger(loader.LOG.name + ".TrackerConnector")
        self.loader = loader
        self.tracker_count = 0
        self.lock = threading.Lock()

    def start(self):
        urls = self.loader.torrent.announce_list
        index = 0
        for tracker_url in urls:
            if tracker_url.startswith(b"udp"):
                TrackerConnection(
                    self, tracker_url, _connect_udp, index).start()
            elif tracker_url.startswith(b"http"):
                TrackerConnection(
                    self, tracker_url, _connect_http, index).start()
            self.increase_tracker_count()
            index += 1
        while True:
            time.sleep(15)
            if self.tracker_count == 0:
                self.LOG.fatal("PANIC!!! Trackers ended.")
                return

    def increase_tracker_count(self):
        self.lock.acquire()
        self.tracker_count += 1
        self.lock.release()

    def decrease_tracker_count(self):
        self.lock.acquire()
        self.tracker_count -= 1
        self.lock.release()


class TrackerConnection(threading.Thread):
    def __init__(self, connector: TrackersConnector, tracker_url,
                 connection_method, connection_index: int):
        threading.Thread.__init__(self)
        self.LOG = logging.getLogger(
            connector.loader.LOG.name + ".TrackerConnection.%d"
            % connection_index)
        self.loader = connector.loader
        self.connector = connector
        self._tracker_url = tracker_url
        self.connection_index = connection_index
        self.peers_count = 0
        self.peers = set()
        self._connect = connection_method
        self.lock = threading.Lock()

    def run(self):
        self.LOG.info("START connecting with " + self._tracker_url.decode())
        first_answer = self._try_connect_tracker_first_time()
        if first_answer is None:
            self.connector.decrease_tracker_count()
            self.LOG.info("START failed to connect with " +
                          self._tracker_url.decode())
            return
        self.LOG.info("START got peers from " + self._tracker_url.decode())
        peers = _parse_peers_ip_and_port(first_answer)
        self._connect_peers(peers)

        # Hmmm? TODO: правильное отслеживание количества пиров и ведение отчетности
        while self.loader.is_working:
            time.sleep(5)
            self.lock.acquire()
            if self.peers_count < MIN_PEERS_COUNT:
                self.LOG.info("RUN Current peers number from '%s': %d"
                              % (self._tracker_url.decode(), self.peers_count))
                self.LOG.info("RUN Ask tracker '%s' for more peers"
                              % self._tracker_url.decode())
                answer = self._try_connect_tracker_for_more_peers()
                if answer is None:
                    self.connector.decrease_tracker_count()
                    self.LOG.fatal("RUN Tracker '%s' do not answer"
                                   % self._tracker_url.decode())
                    return
                peers = _parse_peers_ip_and_port(answer)
                self._connect_peers(peers)
            self.lock.release()
        self.LOG.info("RUN connection with tracker ends "
                      "because loader finished his work")

    def _try_connect_tracker_first_time(self):
        # ip =
        left = self.loader.allocator.get_left_bytes_count()
        params = {
            "info_hash": self.loader.torrent.info_hash,
            "peer_id": self.loader.get_peer_id(),
            "port": 6889 + self.connection_index,  # попробовать другие
            "uploaded": 0,
            "downloaded": 0,
            "left": left,
            "event": "started",
        }
        return self._connect(self._tracker_url, params, self.LOG)

    def _try_connect_tracker_for_more_peers(self):
        left = self.loader.allocator.get_left_bytes_count()
        downloaded = self.loader.torrent.length - left
        params = {
            "info_hash": self.loader.torrent.info_hash,
            "peer_id": self.loader.get_peer_id(),
            "port": 6889 + self.connection_index,  # попробовать другие
            "uploaded": downloaded // 2,  # TODO: скорректировать текущие цифры
            "downloaded": downloaded,
            "left": left,
            "numwant": NUMWANT
        }
        return self._connect(self._tracker_url, params, self.LOG)

    def _connect_peers(self, peers):
        for peer in peers:
            _thread = PeerConnection(peer, self.loader, self, self.loader.allocator)
            _thread.start()
            self.increase_peers_count(_thread)

    def increase_peers_count(self, peer):
        self.peers_count += 1
        self.peers.add(peer)

    def decrease_peers_count(self, peer):
        self.lock.acquire()
        if peer in self.peers:
            self.peers.remove(peer)
        self.peers_count -= 1
        self.lock.release()
