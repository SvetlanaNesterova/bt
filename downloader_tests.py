from unittest import TestCase
from downloader import Loader
import os


class LoaderTests(TestCase):
    def test_file_is_not_torrent_raise_exception(self):
        file = open("samples\\1.txt", "w")
        file.close()
        self.assertRaises(ValueError, Loader, "samples\\1.txt")
        os.remove(os.path.abspath('samples\\1.txt'))


    def test_parse_torrent(self):
        file_name = ""
        #file_name = "Sergey-Kara-Murza-1917-Dve-revolyucii-dva-proekta-2017-FB2.torrent"
        file_name = "Chip-1-Rossiya-Yanvar-2018-PDF.torrent"
        loader = Loader(os.path.abspath("samples\\" + file_name))
        loader.download()
