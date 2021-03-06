import os
from unittest import TestCase
from downloader import Loader
from tracker import _parse_peers_ip_and_port


class LoaderTests(TestCase):
    def test_file_is_not_torrent_raise_exception(self):
        file = open("samples\\1.txt", "w")
        file.close()
        self.assertRaises(ValueError, Loader, "samples\\1.txt")
        os.remove(os.path.abspath('samples\\1.txt'))

    def test_parse_peers(self):
        ans = dict()
        ans[b"peers"] = b"\x01\x02\x03\x04\x05\x06" \
                        b"\x07\x08\x09\x0a\x0b\x0c"
        peers = _parse_peers_ip_and_port(ans)
        expected = [("1.2.3.4", 1286), ("7.8.9.10", 2828)]
        self.assertListEqual(expected, peers)
