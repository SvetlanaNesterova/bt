import time
import requests
import threading
from bencode_parser import BencodeParser
from bencode_translator import BencodeTranslator
from peer_connection import PeerConnection


def _parse_peers_ip_and_port(tracker_answer):
    peers = []
    addresses = tracker_answer[b"peers"]
    for i in range(0, len(addresses), 6):
        peer_info = addresses[i:i + 6]
        peer_ip = ".".join(str(byte) for byte in peer_info[:4])
        peer_port = int.from_bytes(peer_info[4:6], byteorder='big')
        peers.append((peer_ip, peer_port))
    return peers


class PieceState:
    def __init__(self, number, _hash):
        self.state = "no"
        self.number = number
        self.hash = _hash

    def __str__(self):
        return str(self.number) + self.state


class TrackerConnection(threading.Thread):
    def __init__(self, loader):
        threading.Thread.__init__(self)
        self.loader = loader
        self._tracker_url = None
        self.peers_count = 0
        _hashes = self.loader.torrent.pieces_hashes
        self.states = [PieceState(i, _hashes[i]) for i in range(len(_hashes))]

    def run(self):
        first_answer = self._get_peers_first_time()
        peers = _parse_peers_ip_and_port(first_answer)
        self._connect_peers(peers)

        # Hmmm? TODO: правильное отслеживание количества пиров и ведение отчетности
        while self.loader.is_working:
            time.sleep(5)
            lock = threading.Lock()  # А нужен ли тут лок?
            lock.acquire()
            if self.peers_count < 20:
                answer = self._get_peers()
                peers = _parse_peers_ip_and_port(answer)
                self._connect_peers(peers)
            lock.release()
            print("Current peers number: ", self.peers_count)

    def _connect_peers(self, peers):
        for peer in peers:
            _thread = PeerConnection(peer, self.loader, self, self.loader.allocator)
            _thread.start()

            lock = threading.Lock()
            lock.acquire()
            self.peers_count += 1
            lock.release()

    def _get_peers_first_time(self):
        urls = self.loader.torrent.announce_list
        for tracker_url in urls:
            result = self._try_connect_tracker_first_time(tracker_url)
            if result is not None:
                return result
        raise ConnectionError("Failed to connect with any of "
                              "torrent trackers")

    def _get_peers(self):
        return self._try_connect_tracker_for_more_peers()

    def _try_connect_tracker_first_time(self, tracker_url):
        if tracker_url.startswith(b"udp"):
            pass
        elif tracker_url.startswith(b"http"):
            print("Try " + str(tracker_url))
            # ip =
            left = self.loader.allocator.get_left_bytes_count()
            params = {
                "info_hash": self.loader.torrent.info_hash,
                "peer_id": self.loader.get_peer_id(),
                "port": 6889,  # попробовать другие
                "uploaded": "0",
                "downloaded": "0",
                "left": str(left),
                "event": "started",
            }
            return self._connect_http(tracker_url, params)

    def _try_connect_tracker_for_more_peers(self):
        left = self.loader.allocator.get_left_bytes_count()
        downloaded = self.loader.torrent.length - left
        params = {
            "info_hash": self.loader.torrent.info_hash,
            "peer_id": self.loader.get_peer_id(),
            "port": 6889,  # попробовать другие
            "uploaded": "0",  # TODO: скорректировать текущие цифры
            "downloaded": str(downloaded),
            "left": str(left),
            "numwant": 10
        }
        return self._connect_http(self._tracker_url, params)

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
