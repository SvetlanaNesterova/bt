Bittorrent Client

Автор: Нестерова Светлана, группа ФИИТ-202

ОПИСАНИЕ:
Реализовано скачивание одно- и многофайловых торрентов, выборочное скачивание,
скачивание больших файлов. Программа имеет консольный интерфейс

ТРЕБОВАНИЯ:
Python версии не ниже 3.5.1
Библотека requests

Состав
Папка 'samples' - примеры торрент файлов (хороший торрент "mi.torrent")
Папка 'results' - для результатов загрузки
                  (выбирать для этого также можно любую другую папку)
Папка 'logs' - логи (в случае ошибок, пожалуйста, вышлите логи и копию текста из консоли)

ИСПОЛЬЗОВАНИЕ
Запуск из корневой директории проекта:
>python main.py

С проверкой работоспособности возникает много проблем, из-за того, что сейчас
многие торрент-треккеры не работают (сторонние торрент-клиенты это подтверждают).
Торрент с индийской музыкой из примера (см. ниже) у меня скачивался хорошо
и по частям, и целиком.

ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
На примере торрента с индийской музыкой "mi.torrent" из папки "samples"
показано, как добавить торрент, выбрать в нем конкретные файлы для загрузки,
начать скачивание и проверять состояние скачивания вплоть до завершения.

Действия, показанные ниже (кроме проверки состояния командами show и show_all),
также можно выполнить в консольном интерфейсе с помощью короткой команды "sample"

***НАЧАЛО ПРИМЕРА***
>>> add_torrent samples\mi.torrent
~ Torrent 'mi.torrent'
~ was successfully added to the list of torrents with id 1.
~ To select files for downloading in this torrent use 'select [torrent_id]'.
~ To start downloading write command 'download [torrent_id] [save_path]'.
~ To see list of all added torrents write command 'show_all'.
>>> select 1
~ Open file '1.select' in text redactor and correct it.
~ Every line in this file matches file in torrent with id 1,
~ name: 'mi.torrent'
~ First symbol of line should be '+' or '-' depending on
~ whether you would like to download this file or not.
~ Save corrected file and write command 'save_select [torrent_id]'
>>> save_select 1
~ Selection was saved for torrent 1
>>> show_all
 ID |       Name       |  Stage  | Status |  Files  |       Size      |Progress
   1|                mi| selected|      - |     1/20|    8.4Mb/261.0Mb|      -
>>> download 1 results\
Downloading of 'mi.torrent' started
>>> show 1
ID:  1
Name:  mi
Stage:  loading
Status:  peers
Files: selected 1 from 20
Size:  8.4Mb/261.0Mb - selected 8756502 bytes from 273723289 bytes
Progress: 0%
       planned: 8756502 bytes (17 pieces)
    downloaded: 0 bytes (0 pieces)
          left: 8756502 bytes (17 pieces)

Start time:  Tue Mar 13 11:18:06 2018
>>> show_all
 ID |       Name       |  Stage  | Status |  Files  |       Size      |Progress
   1|                mi|  loading|   peers|     1/20|    8.4Mb/261.0Mb|     36%
>>> show_all
 ID |       Name       |  Stage  | Status |  Files  |       Size      |Progress
   1|                mi|  loading|   peers|     1/20|    8.4Mb/261.0Mb|     66%
>>> show 1
ID:  1
Name:  mi
Stage:  loading
Status:  peers
Files: selected 1 from 20
Size:  8.4Mb/261.0Mb - selected 8756502 bytes from 273723289 bytes
Progress: 71%
       planned: 8756502 bytes (17 pieces)
    downloaded: 6223442 bytes (12 pieces)
          left: 2533060 bytes (5 pieces)

Start time:  Tue Mar 13 11:18:06 2018
>>> show_all
 ID |       Name       |  Stage  | Status |  Files  |       Size      |Progress
   1|                mi| finished|   peers|     1/20|    8.4Mb/261.0Mb|    100%
>>> show 1
ID:  1
Name:  mi
Stage:  finished
Status:  peers
Files: selected 1 from 20
Size:  8.4Mb/261.0Mb - selected 8756502 bytes from 273723289 bytes
Progress: 100%
       planned: 8756502 bytes (17 pieces)
    downloaded: 8756502 bytes (17 pieces)
          left: 0 bytes (0 pieces)

Start time:  Tue Mar 13 11:18:06 2018
Finish time:  Tue Mar 13 11:25:18 2018
>>> exit

***КОНЕЦ ПРИМЕРА***