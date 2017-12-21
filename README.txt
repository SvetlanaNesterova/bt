import hashlib
h = hashlib.sha1()
h.update("abcd".encode())
h.digest()


Если вы хотите найти место куда пользовательские
данные можно положить, то appdirs модуль предоставляет
переносимый способ:

import appdirs   # $ pip install appdirs

user_data_dir = appdirs.user_data_dir("Название приложения",
                                        "Кто создал")

TODO: выделить сущность словаря торрента, с полями info и т.д

протокола BitTorrent v 1.0
http://www.bittorrent.org/beps/bep_0003.html