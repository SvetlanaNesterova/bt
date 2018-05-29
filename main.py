import sys
import os
import time
import math
import logging
import traceback
from pathlib import Path
import downloader


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

def convert_bytes_size(size_b):
    if size_b <= 1024:
        return "{:4.1f}".format(size_b) + "b"
    size_kb = size_b / 1024
    if size_kb <= 1024:
        return "{:4.1f}".format(size_kb) + "Kb"
    size_mb = size_kb / 1024
    if size_mb <= 1024:
        return "{:4.1f}".format(size_mb) + "Mb"
    size_gb = size_mb / 1024
    return "{:4.1f}".format(size_gb) + "Gb"

class DownloadingInfo:
    def __init__(self, loader: downloader.Loader, _id: int):
        self.loader = loader
        self.name = Path(loader.torrent_file_path).name
        self.add_time = time.asctime()
        self.start_download_time = None
        self.files = loader.torrent.files
        self.identifier = _id
        self.is_selecting = False
        self.is_selected = False
        self.is_load_started = False

    def download(self):
        self.loader.start()

    def set_save_path(self, path):
        self.loader.set_save_path(path)


class ConsoleInterface:
    def __init__(self):
        self.actions = {
            "help": self.print_help,
            "exit": self.print_goodbye,
            "cats": self.print_cats,
            "add_torrent": self.add_torrent,
            "select": self.select_files_in_torrent,
            "download": self.start_downloading,
            "show": self.show_torrent_info,
            "show_all": self.show_all_info,
            'save_select': self.save_select,
            'sample': self.sample
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
            except KeyboardInterrupt:
                self.print_goodbye(["exit"])
            if not args:
                continue
            command = args[0]
            if command in self.actions:
                self.actions[command](args)
            else:
                self.print_error("No such command '%s'" % command)

    def print_header(self):
        print(" /\ _ /\                                                     ")
        print("(  (_)  )       /\___/\                  _~_~_               ")
        print(" \/ _ \/ _    _(__   __)                |  ___|          _   ")
        print(" | (_) )(_) _| |_ | |  ___   _  _  _  _ | |___  _  __  _| |_ ")
        print(" |  _ (  _ (_   _)| | / _ \ | |/_)| |/_)|  ___|| |/_ \(_   _)")
        print(" | (_) )| |  | |  | || (_) ||  /  |  /  | |___ |  / | | | |  ")
        print(" |____/ |_|  |_|  |_| \___/ |_|   |_|   |_____||_|  |_| |_|  ")
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
            "             /\_/\                    _"
            "_..--''''---....___   _..._    __    \n"
            "(.  /\_ /\  >^,^ < ,/\/\          _.-' "
            "  .-/\";  '         ''<._  ''.''_ '. \n"
            " .)_>^,^<     / \\  (0.0 )     _.-' _.."
            "--.' ^    >                   '( ) ) \n"
            "(____(__)  <_(__), /    \    (_..-'    "
            "(<  ^     ;_..__               ; ''  \n"
            "                   v v  c)_S'          "
            " `-._,_)'      ''--...____..-'       \n"
            "\n"
        )

    def print_goodbye(self, args):
        if len(args) != 1:
            self.print_error("Command 'exit' takes no argument")
            return
        print()
        print("GOODBYE!!! <3")
        LOG.info("Ended CUI\n\n")
        sys.exit(0)

    def print_help(self, args):
        if len(args) != 1:
            self.print_error("Command 'help' takes no argument")
        print("Notice: command should be written in "
              "snake_case (with '_' between words)\n")
        print("  add_torrent [file_path]        "
              "Add new torrent-file for downloading")
        print("  cats                           Cats")
        print("  select [torrent_id]            "
              "Select files for downloading in torrent")
        print("  save_select [torrent_id]       "
              "Save selected (use after 'select [torrent_id]')")
        print("  download [torrent_id]          "
              "Start downloading torrent with this identifier\n"
              "  [save_path]                    "
              "in directory save_path. After start of\n"
              "                                 "
              "downloading selected files cannot be changed")
        print("  show [torrent_id]              "
              "Show info about torrent with this identifier")
        print("  show_all                       "
              "Show list of added torrents")
        print("  sample                         "
              "Add, select and download sample torrent\n"
              "                                 "
              "with Indian music automaticlly")
        print("  exit                           "
              "End executing")

    def sample(self, args):
        if len(args) != 1:
            self.print_error("Command 'sapmle' takes no argument")
            return
        command = "add_torrent samples\mi.torrent"
        print("### " + command)
        try:
            self.add_torrent(command.split())
        except Exception:
            return
        _id = str(len(self.torrents))
        command = "select " + _id
        print("### " + command)
        try:
            self.select_files_in_torrent(command.split())
        except Exception:
            return
        try:
            file_name = _id + ".select"
            with open(file_name, 'rt') as file:
                lines = ['-' + line[1:] for line in file]
            lines[3] = '+' + lines[3][1:]
            with open(file_name, 'wt') as file:
                file.writelines(lines)
        except Exception:
            return
        command = "save_select " + _id
        print("### " + command)
        try:
            self.save_select(command.split())
        except Exception:
            return
        command = "download " + _id + " results\\"
        print("### " + command)
        try:
            self.start_downloading(command.split())
        except Exception:
            return

    def add_torrent(self, args):
        if len(args) < 2:
            self.print_error("Command 'add_torrent' takes one argument: "
                             "name of torrent-file")
            return
        file_name = " ".join(args[1:])
        try:
            new_torrent = DownloadingInfo(
                downloader.Loader(
                    os.path.abspath(file_name)), len(self.torrents) + 1)
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
              "~ was successfully added to the list of "
              "torrents with identifier %d.\n"
              "~ To select files for downloading in "
              "this torrent use 'select [torrent_id]'.\n"
              "~ To start downloading write command "
              "'download [torrent_id] [save_path]'.\n"
              "~ To see list of all added torrents write command 'show_all'."
              % (new_torrent.name, len(self.torrents)))

    def check_torrent_id_downloading(self, str_id):
        try:
            torrent_id = int(str_id)
        except ValueError:
            self.print_error("Torrent identifier should be integer number.")
            return None
        if not 0 <= torrent_id - 1 < len(self.torrents):
            self.print_error("No torrent with such identifier.")
            return None
        torrent = self.torrents[torrent_id - 1]
        if torrent.loader.is_working:
            self.print_error("Torrent with identifier %d is already "
                             "downloading" % torrent_id)
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
        torrent.is_load_started = True
        print("Downloading of '%s' started" % torrent.name)

    def select_files_in_torrent(self, args):
        if len(args) != 2:
            self.print_error(
                "Command 'select' takes one argument: torrent_id")
            return
        torrent = self.check_torrent_id_downloading(args[1])
        if torrent is None:
            return
        file_name = str(torrent.identifier) + ".select"
        with open(file_name, 'wt') as file:
            for file_record in torrent.files:
                path = "\\".join(
                    [item.decode() for item in file_record.local_path])
                file.write("+ " + path + "\n")
        torrent.is_selecting = True
        print("~ Open file '%d.select' in text redactor and correct it.\n"
              "~ Every line in this file matches file in torrent with "
              "identifier %d,\n~ name: '%s'\n"
              "~ First symbol of line should be '+' or '-' depending on\n"
              "~ whether you would like to download this file or not."
              % (torrent.identifier, torrent.identifier, torrent.name))
        print("~ Save corrected file and write "
              "command 'save_select [torrent_id]'")

    def save_select(self, args):
        if len(args) != 2:
            self.print_error(
                "Command 'select' takes one argument: torrent_id")
            return
        torrent = self.check_torrent_id_downloading(args[1])
        if torrent is None:
            return
        if not torrent.is_selecting:
            self.print_error("This torrent wasn't declared for selection. "
                             "Use 'select [torrent_id]' first")
            return
        file_name = str(torrent.identifier) + ".select"
        with open(file_name, 'rt') as file:
            index = 0
            for line in file.readlines():
                index += 1
                if line[0] != "+" and line[0] != "-":
                    self.print_error("Wrong first symbol in line № %d:\n%s"
                                     % (index, line))
                    return
            file.seek(0)
            for line, file_record in zip(file.readlines(), torrent.files):
                file_record.is_downloading = (line[0] == "+")
        torrent.is_selected = True
        print("~ Selection was saved for torrent %d" % torrent.identifier)

    def show_torrent_info(self, args):
        if len(args) != 2:
            self.print_error("Command 'show' takes "
                             "one argument: torrent_id")
            return
        try:
            torrent_id = int(args[1])
        except ValueError:
            self.print_error("Torrent identifier should be integer number.")
            return
        if not 0 <= torrent_id - 1 < len(self.torrents):
            self.print_error("No torrent with such identifier.")
            return
        torrent = self.torrents[torrent_id - 1]
        print("ID: ", torrent_id)
        print("Name: ", str(torrent.name)[:-8])
        print("Stage: ", self._get_stage(torrent))
        status = self._get_status(torrent)
        if not '-' in status:
            status = "connecting with " + status
        print("Status: ", status)
        print("Files: selected %d from %d" % self._get_files(torrent))
        round_size = self._get_round_size(torrent)
        exact = self._get_exact_size(torrent)
        print("Size: %s/%s - selected %d bytes from %d bytes"
              % (round_size[0], round_size[1], exact[0], exact[1]))
        if torrent.loader.is_working or torrent.loader.is_finished:
            piece_len = torrent.loader.torrent.piece_length
            planned = torrent.loader.allocator.planned_bytes_count
            loaded = torrent.loader.allocator.get_downloaded_bytes_count()
            left = torrent.loader.allocator.get_left_bytes_count()
            print("Progress: %s\n"
                  "       planned: %d bytes (%d pieces)\n"
                  "    downloaded: %d bytes (%d pieces)\n"
                  "          left: %d bytes (%d pieces)\n"
                  % (self._get_progress(torrent),
                     planned, math.ceil(planned / piece_len),
                     loaded, math.ceil(loaded / piece_len),
                     left, math.ceil(left / piece_len)))
            print("Start time: ",
                  time.ctime(torrent.loader.start_download_time))
            if torrent.loader.is_finished:
                print("Finish time: ",
                      time.ctime(torrent.loader.finish_download_time))
        else:
            print("Progress: -")

    def show_all_info(self, args):
        if len(args) != 1:
            self.print_error("Command 'show_all' takes no argument")
            return
        headers = [
            " ID ",
            "       Name       ",
            "  Stage  ",
            " Status ",
            "  Files  ",
            "       Size      ",
            "Progress"
        ]
        title = "|".join(headers)
        print(title)
        for torrent in self.torrents:
            _id = torrent.identifier
            name = str(torrent.name)[:-8][:18]
            stage = self._get_stage(torrent)
            status = self._get_status(torrent)
            files = "%d/%d" % (self._get_files(torrent))
            size = "%s/%s" % (self._get_round_size(torrent))
            progress = self._get_progress(torrent)
            record = "%4d|%18s|%9s|%8s|%9s|%17s|%8s" \
                     % (_id, name, stage, status, files, size, progress)
            print(record)

    def _get_stage(self, torrent):
        if torrent.loader.is_finished:
            stage = "finished"
        elif torrent.is_load_started:
            if torrent.loader.is_working:
                stage = "loading"
            else:
                stage = "creating"
        elif torrent.is_selected:
            stage = "selected"
        elif torrent.is_selecting:
            stage = "selecting"
        else:
            stage = "added"
        return stage

    def _get_status(self, torrent):
        status = " - "
        if torrent.loader.is_working:
            trackers = torrent.loader.trackers.active_tracker_count()
            if trackers == 0:
                status = "trackers"
            else:
                status = "peers"
        return status

    def _get_files(self, torrent):
        files_all_count = len(torrent.files)
        files_actual_count = 0
        for file in torrent.files:
            files_actual_count += 1 if file.is_downloading else 0
        return files_actual_count, files_all_count

    def _get_round_size(self, torrent):
        actual_size, all_size = self._get_exact_size(torrent)
        all_size = convert_bytes_size(all_size)
        actual_size = convert_bytes_size(actual_size)
        return actual_size, all_size

    def _get_exact_size(self, torrent):
        all_size = torrent.loader.torrent.length
        actual_size = 0
        for file in torrent.files:
            if file.is_downloading:
                actual_size += file.length
        return actual_size, all_size

    def _get_progress(self, torrent):
        progress = " - "
        if torrent.loader.is_working:
            target = torrent.loader.allocator.planned_bytes_count
            actual = torrent.loader.allocator.get_downloaded_bytes_count()
            progress = str(round(100 * actual / target)) + "%"
        return progress


if __name__ == "__main__":
    ConsoleInterface().start()
