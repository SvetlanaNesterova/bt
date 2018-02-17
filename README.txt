Требуется библотека requests

import hashlib
h = hashlib.sha1()
h.update("abcd".encode())
h.digest()

TODO: IPv6

Если вы хотите найти место куда пользовательские
данные можно положить, то appdirs модуль предоставляет
переносимый способ:

import appdirs   # $ pip install appdirs

user_data_dir = appdirs.user_data_dir("Название приложения",
                                        "Кто создал")

http://netall.ucoz.ru/publ/specifikacija_protokola_bittorrent_v_1_0_v_detaljakh_po_russki/1-1-0-25
http://www.bittorrent.org/beps/bep_0003.html

протокола BitTorrent v 1.0
http://www.bittorrent.org/beps/bep_0003.html
UDP tracker protocol
http://www.bittorrent.org/beps/bep_0015.html


Exception in thread Thread-3:
Traceback (most recent call last):
  File "C:\Users\1ё\AppData\Local\Programs\Python\Python36-32\lib\threading.py", line 916, in _bootstrap_inner
    self.run()
  File "C:\Users\1ё\Desktop\Света\Python\bittorrent\peer_connection.py", line 76, in run
    self._check_input_messages()
  File "C:\Users\1ё\Desktop\Света\Python\bittorrent\peer_connection.py", line 115, in _check_input_messages
    self.react[message_type](response)
  File "C:\Users\1ё\Desktop\Света\Python\bittorrent\peer_connection.py", line 188, in _react_piece
    self._allocator.save_piece(piece_index, self._storage, self)
  File "C:\Users\1ё\Desktop\Света\Python\bittorrent\pieces_allocator.py", line 107, in save_piece
    for other_peer in self._peers_pieces_info.keys():
RuntimeError: dictionary changed size during iteration