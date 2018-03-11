import sys
import os
import time
import logging
import traceback
import downloader
from pathlib import Path


LINE_START = ">>> "


def create_logger():
    logger = logging.getLogger("bt.main")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s    %(name)s    %(levelname)s \n'
        '\t   %(message)s')
    file_handler = logging.FileHandler("logs\\bt.main.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


LOG = create_logger()


class DownloadingInfo:
    def __init__(self, torrent: downloader.Loader):
        self.torrent = torrent
        self.name = Path(torrent.torrent_file_path).name
        self.add_time = time.asctime()
        self.start_download_time = None
        self.files = torrent.torrent.files

    def download(self):
        self.torrent.start()
        self.start_download_time = time.asctime()

    def set_save_path(self, path):
        self.torrent.set_save_path(path)


class ConsoleInterface:
    def __init__(self):
        self.actions = {
            "help": self.print_help,
            "exit": self.print_goodbye,
            "cats": self.print_cats,
            "add_torrent": self.add_torrent,
            "add_sample_torrent": self.add_sample_torrent,
            "select_files": self.select_files_in_torrent,
            "download": self.start_downloading,
            "show": self.show_torrent_info,
            "show_all": self.show_all_info,
            'd':self.d
        }
        self.torrents = []

    def start(self):
        LOG.info("Started CUI")
        self.print_header()
        while True:
            try:
                args = input(LINE_START)
                LOG.info("get command '%s'" % args)
                args = args.split()
            except EOFError:
                self.print_goodbye(["exit"])
                break
            except KeyboardInterrupt:
                self.print_goodbye(["exit"])
                break
            if not args:
                continue
            command = args[0]
            if command in self.actions:
                self.actions[command](args)
        LOG.info("Ended CUI\n\n")

    def print_header(self):
        print("    /\ _ /\                                                            <3")
        print("   (  (_)  )       /\___/\                  _~_~_                      <3")
        print("    \/ _ \/ _    _(__   __)                |  ___|           _         <3")
        print("    | (_) )(_) _| |_ | |  ___   _  _  _  _ | |___  _  __   _| |_       <3")
        print("    |  _ (  _ (_   _)| | / _ \ | |/_)| |/_)|  ___|| |/_ \ (_   _)      <3")
        print("    | (_) )| |  | |  | || (_) ||  /  |  /  | |___ |  / | |  | |        <3")
        print("    |____/ |_|  |_|  |_| \___/ |_|   |_|   |_____||_|  |_|  |_|        <3")
        print("")
        print("         By Svetlanka (c)")
        print(LINE_START)
        print(LINE_START)

    def print_error(self, msg):
        LOG.info("Inform about error: " + str(msg))
        print("!!!  " + str(msg))

    def print_cats(self, args):
        if len(args) != 1:
            self.print_error("Command 'cats' takes no argument")
            return
        print(
            "\n"
            "             /\_/\                    __..--''''---....___   _..._    __    \n"
            "(.  /\_ /\  >^,^ < ,/\/\          _.-'   .-/\";  '         ''<._  ''.''_ '. \n"
            " .)_>^,^<     / \\  (0.0 )     _.-' _..--.' ^    >                   '( ) ) \n"
            "(____(__)  <_(__), /    \    (_..-'    (<  ^     ;_..__               ; ''  \n"
            "                   v v  c)_S'           `-._,_)'      ''--...____..-'       \n"
            "\n"
        )

    def print_goodbye(self, args):
        if len(args) != 1:
            self.print_error("Command 'exit' takes no argument")
            return
        print()
        print("GOODBYE!!! <3")

    def print_help(self, args):
        print("Notice: command should be written in "
              "snake_case (with '_' between words)\n")
        print("  add_torrent [file_name]        "
              "Add new torrent-file for downloading")
        print("  add_sample_torrent             "
              "Add sample torrent-file for downloading")
        print("  cats                           Cats")
        print("  select_files [torrent_id]      Config")
        print("  download [torrent_id]          "
              "Start downloading torrent with this id\n"
              "  [save_path]                    "
              "in directory save_path. After start of\n"
              "                                 "
              "downloading selected files cannot be \n"
              "                                 changed")
        print("  show [torrent_id]              "
              "Show info about torrent with this id")
        print("  show_all                       "
              "Show list of added torrents")
        print("  exit                           "
              "End executing")

    def add_torrent(self, args):
        if len(args) < 2:
            self.print_error("Command 'add_torrent' takes one argument: "
                             "name of torrent-file")
            return
        file_name = " ".join(args[1:])
        try:
            new_torrent = DownloadingInfo(
                downloader.Loader(os.path.abspath(file_name)))
        except (FileNotFoundError, IsADirectoryError) as ex:
            self.print_error(ex)
            return
        except Exception as ex:
            LOG.error("Exception '%s'\n"
                      "during initialization of Loader with file '%s'\n %s"
                      % (str(ex), os.path.abspath(file_name),
                         traceback.format_exc()))
            self.print_error("Unexpected error occurred '%s'. "
                             "See logs for more details" % str(ex))
            return
        self.torrents.append(new_torrent)
        print("~ Torrent '%s'\n"
              "~ was successfully added to the list of torrents with id %d.\n"
              "~ To start downloading write command "
              "'download [torrent_id] [save_path]'.\n"
              "~ To see list of all added torrents write command "
              "'show_all'." % (new_torrent.name, len(self.torrents)))

    def add_sample_torrent(self, args):
        if len(args) != 1:
            self.print_error("Command 'add_sample_torrent' takes no argument")
            return
        # file_name = "Sergey-Kara-Murza-1917-Dve-revolyucii-dva-proekta-2017-FB2.torrent"
        # file_name = "Chip-1-Rossiya-Yanvar-2018-PDF.torrent"
        # file_name = "Bruce.Lee.2O17.D.BDRip.14OOMB.avi.torrent"
        # file_name = "Wind.River.2017_HDRip___29735.torrent"
        # file_name = "38585_igra_prestolov_.torrent"
        # file_name = "Chip-1-Rossiya-Yanvar-2018-PDF.torrent"
        # file_name = "Red.Hot.Chili.Peppers.The.Getaway.2016.MP3.torrent"
        file_name = "mi.torrent"
        # file_name = "Мумий тролль.torrent"
        # file_name = "rutor.isevro_hit_top_40_europa_plus_02.02.2018.torrent"
        # loader = Loader(os.path.abspath("samples\\" + file_name),
        #                os.path.abspath("results\\"))
        # loader.download()
        file_name = "samples\\" + file_name
        self.add_torrent(["add_torrent", file_name])

    def check_torrent_id_downloading(self, str_id):
        try:
            torrent_id = int(str_id)
        except ValueError as ex:
            self.print_error("Torrent id should be integer number.")
            return None
        if not (0 <= torrent_id - 1 < len(self.torrents)):
            self.print_error("No torrent with such id.")
            return None
        torrent = self.torrents[torrent_id - 1]
        if torrent.torrent.is_working:
            self.print_error("Torrent with id %d is already downloading" %
                             torrent_id)
            return None
        return torrent

    def start_downloading(self, args):
        if len(args) < 3:
            self.print_error("Command 'download' takes two arguments")
            return
        torrent = self.check_torrent_id_downloading(args[1])
        if torrent is None:
            return
        path = " ".join(args[2:])
        try:
            torrent.set_save_path(os.path.abspath(path))
        except (FileNotFoundError, NotADirectoryError) as ex:
            self.print_error(ex)
            return

        torrent.download()
        print("Downloading of '%s' started" % torrent.name)

    def d(self, args):
        self.add_sample_torrent(["add"])
        #self.select_files_in_torrent(["select", "1"])
        self.start_downloading(["download", "1", "results\\"])

    def select_files_in_torrent(self, args):
        if len(args) != 2:
            self.print_error("Command 'show_torrent_info' takes "
                             "one argument: torrent_id")
            return

        torrent = self.check_torrent_id_downloading(args[1])
        if torrent is None:
            return
        for file_record in torrent.files[1:]:
            file_record.is_downloading = False

    def show_torrent_info(self, args):
        if len(args) != 2:
            self.print_error("Command 'show' takes "
                             "one argument: torrent_id")
            return

    def show_all_info(self, args):
        if len(args) != 1:
            self.print_error("Command 'show_all' takes no argument")
            return


if __name__ == "__main__":
    ConsoleInterface().start()


