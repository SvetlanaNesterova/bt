import time
import threading
import logging
from random import Random
from socket import socket, SOCK_DGRAM, AF_INET, gaierror
import requests
from bencode import BencodeParser
from peer import PeerConnection
from torrent_info import int_to_four_bytes_big_endian, bytes_to_int


MIN_PEERS_COUNT = 50
FIRST_NUMWANT = 50
NUMWANT = 50
PORT = 6889
CHECK_PAUSE_SEC = 5


def _parse_peers_ip_and_port(tracker_answer):
    peers = []
    addresses = tracker_answer[b"peers"]
    if isinstance(addresses, list):
        for peer_info in addresses:
            peer_ip = peer_info[b'ip'].decode()
            peer_port = peer_info[b'port']
            peers.append((peer_ip, peer_port))
        return peers
    else:
        for i in range(0, len(addresses), 6):
            peer_info = addresses[i:i + 6]
            peer_ip = ".".join(str(byte) for byte in peer_info[:4])
            peer_port = int.from_bytes(peer_info[4:6], byteorder='big')
            peers.append((peer_ip, peer_port))
        return peers


def _convert_str_to_pair_address(url):
    temp = url.split(b':')
    port = temp[-1].split(b'/')[0]
    host = url[0: -len(port) - 1].decode()
    return host, int(port)


def _connect_http(tracker_url, params, logger: logging.Logger, loader):
    try:
        response = requests.get(tracker_url, params=params)
        try:
            tracker_answer = BencodeParser.parse(response.content)[0]
            return tracker_answer
        except Exception as ex:
            logger.error("Exception in parsing loader '%s' answer: %s\n %s"
                         % (tracker_url.decode(), str(ex), response.content))
            return None
    except Exception as ex:
        logger.error("Exception during HTTP connection with loader '%s':"
                     "\n %s" % (tracker_url.decode(), str(ex)))
        return None


def _connect_udp(tracker_url, params, logger: logging.Logger, loader):
    logger.info("Try connecting UDP with tracker '%s'" % tracker_url.decode())
    try:
        address = _convert_str_to_pair_address(tracker_url)
    except Exception as ex:
        logger.error("Exception during parsing address '%s': %s"
                     % (tracker_url.decode(), str(ex)))
        return None
    address = (address[0][6:], address[1])
    connection_id = _connect(address, logger, loader)
    if connection_id is None:
        return None
    session_start = time.time()
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    udp_socket.settimeout(15)
    iteration = -1
    while True:
        if iteration > 8:
            logger.error("Failed connecting UDP with tracker '%s' "
                         "during announce: timeout" % tracker_url.decode())
            return None
        if iteration >= 0:
            timeout = 15 * 2 ** iteration
            start = time.time()
            while time.time() - start < timeout:
                time.sleep(15)
                if loader.is_finished or not loader.is_working:
                    logger.info("UDP connection with '%s' ends because loader "
                                "stopped his work" % tracker_url.decode())
                    return None
        if time.time() - session_start >= 59:
            connection_id = _connect(address, logger, loader)
            if connection_id is None:
                return None
            session_start = time.time()
        transaction_id, message = _generate_announce(connection_id, params)
        udp_socket.sendto(message, address)
        try:
            data, recv_address = udp_socket.recvfrom(1024)
            # TODO: какое поведение при отсутствии ответа?
        except Exception as ex:
            logger.error("Exception during getting UDP response in announce "
                         "with Tracker '%s': '%s'"
                         % (tracker_url.decode(), str(ex)))
            iteration += 1
            continue
        recv_transaction_id, action, tracker_answer = \
            _parse_announce_response(data)
        if len(data) < 20 or (len(data) - 20) % 6 != 0 or \
                recv_address != address or action != 1 or \
                recv_transaction_id != transaction_id:
            iteration += 1
            logger.info("Incorrect UDP response in announce "
                        "with Tracker '%s'" % tracker_url.decode())
            continue
        break
    logger.info("Get peers from UDP tracker '%s'" % tracker_url.decode())
    return tracker_answer


def _connect(address, logger: logging.Logger, loader):
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    iteration = -1
    while True:
        if iteration > 8:
            logger.error("Failed connecting UDP with tracker '%s' "
                         "during connect: timeout" % str(address))
            return None
        if iteration >= 0:
            timeout = 15 * 2 ** iteration
            start = time.time()
            while time.time() - start < timeout:
                time.sleep(15)
                if loader.is_finished or not loader.is_working:
                    logger.info("UDP connection with '%s' ends because loader "
                                "stopped his work" % str(address))
                    return None
        transaction_id, message = _generate_connect_request()
        try:
            udp_socket.sendto(message, address)
        except gaierror as ex:
            logger.error("Exception sending UDP connect to tracker '%s': '%s'"
                         % (str(address), str(ex)))
        udp_socket.settimeout(15)
        try:
            data, recv_address = udp_socket.recvfrom(16)
            # TODO: достаточная ли проверка длины
        except Exception as ex:
            logger.error("Exception during getting UDP response in connect "
                         "with Tracker '%s': '%s'"
                         % (str(address), str(ex)))
            iteration += 1
            continue
        action, recv_transaction_id, connection_id = \
            _parse_connect_response(data)
        if recv_address != address or action != 0 or \
                recv_transaction_id != transaction_id:
            logger.info("Incorrect UDP response in connect "
                        "with Tracker '%s'" % str(address))
            iteration += 1
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


def _generate_announce(connection_id, params):
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
    ip_address = int_to_four_bytes_big_endian(0)
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
        event + ip_address + key + num_want + port
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
        self.log = logging.getLogger(loader.log.name + ".TrackerConnector")
        self.loader = loader
        self.tracker_count = 0
        self.trackers = set()
        self.lock = threading.Lock()
        self.peers_lock = threading.Lock()
        self.peers_count = 0
        self.peers = set()
        self.finished = False

    def start(self):
        urls = self.loader.torrent.announce_list
        index = 0
        for tracker_url in urls:
            if tracker_url.startswith(b"udp"):
                tracker = TrackerConnection(
                    self, tracker_url, _connect_udp, index)
                tracker.start()
            elif tracker_url.startswith(b"http"):
                tracker = TrackerConnection(
                    self, tracker_url, _connect_http, index)
                tracker.start()
            else:
                continue
            self.add_tracker(tracker)
            index += 1
        while True:
            time.sleep(15)
            if self.finished:
                self.log.info("Connector finished")
                return
            if self.tracker_count == 0:
                self.log.fatal("PANIC! Trackers ended.")
                self.tracker_count = -1
            if self.tracker_count == -1 and self.peers_count == 0:
                self.log.fatal("PANIC!!! Trackers and all peers ended. "
                               "Connector finishes its work")
                return

    def finish(self):
        self.finished = True

    def add_tracker(self, tracker):
        with self.lock:
            self.tracker_count += 1
            self.trackers.add(tracker)

    def decrease_tracker_count(self, tracker):
        with self.lock:
            self.tracker_count -= 1
            self.trackers.remove(tracker)

    def active_tracker_count(self):
        with self.lock:
            count = 0
            for tracker in self.trackers:
                if tracker.give_peers:
                    count += 1
            return count

    def add_peer(self, peer):
        with self.peers_lock:
            self.peers_count += 1
            self.peers.add(peer)

    def delete_peer(self, peer):
        with self.peers_lock:
            if peer in self.peers:
                self.peers.remove(peer)
            self.peers_count -= 1

class TrackerConnection(threading.Thread):
    def __init__(self, connector: TrackersConnector, tracker_url,
                 connection_method, connection_index: int):
        threading.Thread.__init__(self)
        self.log = logging.getLogger(
            connector.loader.log.name + ".TrackerConnection.%d"
            % connection_index)
        self.loader = connector.loader
        self.connector = connector
        self._tracker_url = tracker_url
        self.tracker_index = connection_index
        self.give_peers = False
        self.interval_sec = None
        self.last_time = None
        self._connect = connection_method
        self.lock = threading.Lock()

    def run(self):
        tr_url = self._tracker_url.decode()
        self.log.info("Start connecting with " + tr_url)
        first_answer = self._try_connect_tracker_first_time()
        if first_answer is None:
            self.connector.decrease_tracker_count(self)
            self.log.info("Failed to connect with " + tr_url)
            return
        self.log.info("Got peers from " + tr_url)

        if b"failure reason" in first_answer:
            failure_reason = first_answer[b"failure reason"].decode()
            self.log.error("Failed to get peers from tracker '%s' first time:"
                           "\n%s" % (tr_url, failure_reason))
            return
        self.interval_sec = int(first_answer[b"interval"])
        self.last_time = time.time()
        peers = _parse_peers_ip_and_port(first_answer)
        self._connect_peers(peers)

        while self.loader.is_working and not self.loader.is_finished:
            time.sleep(CHECK_PAUSE_SEC)
            if self.connector.peers_count < MIN_PEERS_COUNT:
                self.log.info("Current peers count: %d. '%s' ask for more..."
                              % (self.connector.peers_count, tr_url))
                answer = self._try_connect_tracker_for_more_peers(NUMWANT)
                action = "get peers from"
            elif self.last_time - time.time() > self.interval_sec:
                answer = self._try_connect_tracker_for_more_peers(0)
                action = "send info to"
            else:
                continue

            if answer is None:
                self.connector.decrease_tracker_count(self)
                self.log.fatal("Tracker '%s' do not answer" % tr_url)
                return
            if b"failure reason" in first_answer:
                failure_reason = first_answer[b"failure reason"].decode()
                self.log.fatal("Failed to %s tracker '%s': %s\n"
                               % (action, tr_url, failure_reason))
                return
            self.interval_sec = int(first_answer[b"interval"])
            self.last_time = time.time()
            peers = _parse_peers_ip_and_port(answer)
            self._connect_peers(peers)
        self.log.info("Connection with tracker '%s' ends because loader "
                      "stopped his work" % tr_url)

    def _try_connect_tracker_first_time(self):
        left = self.loader.allocator.get_left_bytes_count()
        uploaded = self.loader.allocator.get_uploaded_bytes_count()
        downloaded = self.loader.allocator.get_downloaded_bytes_count()
        params = {
            "info_hash": self.loader.torrent.info_hash,
            "peer_id": self.loader.get_peer_id(),
            "port": PORT,
            "uploaded": uploaded,
            "downloaded": downloaded,
            "left": left,
            "event": "started",
        }
        return self._connect(self._tracker_url, params, self.log, self.loader)

    def _try_connect_tracker_for_more_peers(self, numwant):
        left = self.loader.allocator.get_left_bytes_count()
        uploaded = self.loader.allocator.get_uploaded_bytes_count()
        downloaded = self.loader.allocator.get_downloaded_bytes_count()
        params = {
            "info_hash": self.loader.torrent.info_hash,
            "peer_id": self.loader.get_peer_id(),
            "port": PORT,
            "uploaded": uploaded,
            "downloaded": downloaded,
            "left": left,
            "numwant": numwant
        }
        return self._connect(self._tracker_url, params, self.log, self.loader)

    def _connect_peers(self, peers):
        self.give_peers = True
        for peer_address in peers:
            new_peer = PeerConnection(peer_address, self.loader,
                                      self, self.loader.allocator)
            new_peer.start()
            self.connector.add_peer(new_peer)
