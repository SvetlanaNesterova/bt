import os
from downloader import Loader
from peer_connection import PeerConnection

#file_name = "Sergey-Kara-Murza-1917-Dve-revolyucii-dva-proekta-2017-FB2.torrent"
#file_name = "Chip-1-Rossiya-Yanvar-2018-PDF.torrent"
file_name = "Bruce.Lee.2O17.D.BDRip.14OOMB.avi.torrent"
#file_name = "Wind.River.2017_HDRip___29735.torrent"
file_name = "38585_igra_prestolov_.torrent"
#file_name = "Chip-1-Rossiya-Yanvar-2018-PDF.torrent"
file_name = "Red.Hot.Chili.Peppers.The.Getaway.2016.MP3.torrent"
loader = Loader(os.path.abspath("samples\\" + file_name),
                os.path.abspath("results\\"))
loader.download()
