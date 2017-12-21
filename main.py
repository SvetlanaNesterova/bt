import os
from downloader import Loader

file_name = ""
file_name = "Sergey-Kara-Murza-1917-Dve-revolyucii-dva-proekta-2017-FB2.torrent"
#file_name = "Chip-1-Rossiya-Yanvar-2018-PDF.torrent"
# file_name = "38585_igra_prestolov_.torrent"
#file_name = "Bruce.Lee.2O17.D.BDRip.14OOMB.avi.torrent"
file_name = "Wind.River.2017_HDRip___29735.torrent"
loader = Loader(os.path.abspath("samples\\" + file_name))
loader.download()
