import logging
import time
from pathlib import Path
import threading

from bencode import BencodeParser
from tracker import TrackersConnector
from pieces_allocator import Allocator
from torrent_info import TorrentMeta


def _check_file_correctness(file_path: str):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError("No such file '%s'" % str(path))
    if not path.is_file():
        raise IsADirectoryError("No such file '%s'\n"
                                "You should specify file, not directory"
                                % str(path))
    if path.suffix != ".torrent":
        raise FileNotFoundError("Loader takes .torrent file, but file "
                                "extension was: " + path.suffix)


def _check_directory_correctness(dir_path: str):
    path = Path(dir_path)
    if not path.exists():
        raise FileNotFoundError("No such directory '%s'" % str(path))
    if not path.is_dir():
        raise NotADirectoryError("No such directory '%s'\n"
                                 "You should specify directory, not file"
                                 % str(path))


def _read_source_from_file(torrent_file_path: str):
    with open(torrent_file_path, 'rb') as meta:
        source = meta.read()
    return source


MODULE_LOG_NAME = "bt.Loader"


class Loader(threading.Thread):
    count = 0

    @staticmethod
    def _get_logger():
        Loader.count += 1
        log_name = MODULE_LOG_NAME + "." + str(Loader.count)
        logger = logging.getLogger(log_name)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s    %(threadName)s    %(name)s    %(levelname)s \n'
            '\t   %(message)s')
        file_handler = logging.FileHandler("logs\\" + log_name + ".log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    @staticmethod
    def get_peer_id():
        return ("-" + "MY" + "0001" + "-" + "123456789012").encode()

    def __init__(self, torrent_file_path: str):
        if not isinstance(torrent_file_path, str):
            raise TypeError("Loader takes string as file_path")
        _check_file_correctness(torrent_file_path)
        threading.Thread.__init__(self)
        self.name = "Loader." + self.name
        self.log = Loader._get_logger()
        self.log.info("\n\nStart " + Path(torrent_file_path).name)

        self.torrent_file_path = torrent_file_path
        self.save_directory_path = None
        try:
            source = _read_source_from_file(torrent_file_path)
        except Exception as ex:
            ex = "Exception during reading torrent-file: " + str(ex)
            self.log.error(ex)
            print("!!! " + ex)
            return
        try:
            content = BencodeParser.parse(source)[0]
        except Exception as ex:
            ex = "Exception during parsing torrent-file: " + str(ex)
            self.log.error(ex)
            print("!!! " + ex)
            return
        self.log.info("INIT. Parsed torrent file successfully. "
                      "File path: %s" % self.torrent_file_path)
        self.torrent = TorrentMeta(content, self.log.name)
        self.log.info("INIT. Interpreted torrent file successfully")
        self.allocator = None
        self.trackers = TrackersConnector(self)
        self.is_working = False
        self.is_finished = False
        self.start_download_time = None
        self.finish_download_time = None

    def set_save_path(self, save_path: str):
        if not isinstance(save_path, str):
            raise TypeError("Loader takes string as file_path")
        try:
            _check_directory_correctness(save_path)
        except ValueError as ex:
            self.log.info("Exception (throwed) '%s': wrong save path '%s'"
                          % (str(ex), save_path))
            raise ex
        self.save_directory_path = save_path

    def run(self):
        self.log.info("START Start creating empty files")
        self.start_download_time = time.time()
        self.allocator = Allocator(self.torrent,
                                   self.save_directory_path,
                                   self.log,
                                   self)
        self.is_working = True
        self.log.info("START Start connecting with trackers")
        self.trackers.start()

    def finish_downloading(self):
        self.trackers.finish()
        self.is_finished = True
        self.finish_download_time = time.time()

    def get_piece_hash(self, piece_index: int):
        return self.torrent.pieces_hashes[piece_index]

    def get_save_dir_path(self):
        return self.save_directory_path
