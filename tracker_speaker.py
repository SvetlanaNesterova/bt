import time
import requests
import threading
from bencode import BencodeParser, BencodeTranslator
from peer import PeerConnection


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


class TrackersConnector:
    def __init__(self, loader):
        self.loader = loader
        self._tracker_url = None
        self.tracker_count = 0
        self.lock = threading.Lock()

    def start(self):
        urls = self.loader.torrent.announce_list
        for tracker_url in urls:
            if tracker_url.startswith(b"udp"):
                TrackerConnection(
                    self, tracker_url, self._connect_udp).start()
            elif tracker_url.startswith(b"http"):
                TrackerConnection(
                    self, tracker_url, self._connect_http).start()
            self.increase_tracker_count()
        while True:
            time.sleep(15)
            if self.tracker_count == 0:
                print("PANIC!!! Trackers ended.")
                return

    def increase_tracker_count(self):
        self.lock.acquire()
        self.tracker_count += 1
        self.lock.release()

    def decrease_tracker_count(self):
        self.lock.acquire()
        self.tracker_count -= 1
        self.lock.release()

    def _connect_http(self, tracker_url, params):
        try:
            response = requests.get(tracker_url, params=params)
            try:
                result = BencodeParser.parse(response.content)
                BencodeTranslator.print_bencode(result[0])
                self._tracker_url = tracker_url
                self._tracker_answer = result[0]
                return result[0]
            except Exception as e:
                print("EXCEPTION")
                print(e)
                return None
        except Exception as e:
            print("BAD REQUEST")
            print(e)
            return None

    def _connect_udp(self, tracker_url, params):
        pass


class TrackerConnection(threading.Thread):
    def __init__(self, connector: TrackersConnector, tracker_url, connection_method):
        threading.Thread.__init__(self)
        self.loader = connector.loader
        self.connector = connector
        self._tracker_url = tracker_url
        self.peers_count = 0
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
            time.sleep(5)
            self.lock.acquire()
            if self.peers_count < 20:
                answer = self._try_connect_tracker_for_more_peers()
                if answer is None:
                    self.connector.decrease_tracker_count()
                    return
                peers = _parse_peers_ip_and_port(answer)
                self._connect_peers(peers)
            self.lock.release()
            print("Current peers number: ", self.peers_count)

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
            "uploaded": 0,  # TODO: скорректировать текущие цифры
            "downloaded": downloaded,
            "left": left,
            "numwant": 10 # TODO: скорректировать
        }
        return self._connect(self._tracker_url, params)

    def _connect_peers(self, peers):
        for peer in peers:
            _thread = PeerConnection(peer, self.loader, self, self.loader.allocator)
            _thread.start()
            self.increase_peers_count()

    def increase_peers_count(self):
        self.lock.acquire()
        self.peers_count += 1
        self.lock.release()

    def decrease_peers_count(self):
        self.lock.acquire()
        self.peers_count += 1
        self.lock.release()