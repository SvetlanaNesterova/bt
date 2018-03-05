import sys
import os
from downloader import Loader

LINE_START = ">>> "

class ConsoleInterface:
    def __init__(self):
        self.actions = {
            "help": self.print_help,
            "exit": self.print_goodbye,
            "cats": self.print_cats,
            "add_torrent": self.add_torrent,
            "add_sample_torrent": self.add_sample_torrent
        }
        self.torrents = []
        pass

    def start(self):
        self.print_header()
        while True:
            try:
                args = input(LINE_START).split()
            except EOFError:
                self.print_goodbye([])
            except KeyboardInterrupt:
                self.print_goodbye([])
            command = args[0]
            if command in self.actions:
                self.actions[command](args)

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
        print("!!!  " + msg)

    def print_cats(self, args):
        if len(args) > 1:
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
        if len(args) > 1:
            self.print_error("Command 'exit' takes no argument")
            return
        print()
        print("GOODBYE!!! <3")
        sys.exit(0)

    def print_help(self, args):
        print("  exit                      End executing")
        print("  add_torrent [file_name]   Add new torrent-file "
              "for downloading")
        print("  add_sample_torrent        Add sample torrent-file "
              "for downloading")
        print("  cats                      Cats")

    def add_torrent(self, args):
        if len(args) > 2:
            self.print_error("Command 'add_torrent' takes one argument: "
                        "name of torrent-file")
            return
        file_name = args[1]
        new_torrent = Loader(os.path.abspath(file_name),
                             os.path.abspath("results\\"))
        self.torrents.append(new_torrent)
        print("Torrent was successfully added to the list of torrents "
              "with id %d.\n"
              "To start downloading write command "
              "'download [torrent_id]'.\n"
              "To see list of all added torrents write command "
              "'show_all'." % len(self.torrents))

    def add_sample_torrent(self, args):
        if len(args) > 2:
            self.print_error(
                "Command 'add_sample_torrent' takes no argument")
            return
        # file_name = "Sergey-Kara-Murza-1917-Dve-revolyucii-dva-proekta-2017-FB2.torrent"
        # file_name = "Chip-1-Rossiya-Yanvar-2018-PDF.torrent"
        # file_name = "Bruce.Lee.2O17.D.BDRip.14OOMB.avi.torrent"
        # file_name = "Wind.River.2017_HDRip___29735.torrent"
        # file_name = "38585_igra_prestolov_.torrent"
        # file_name = "Chip-1-Rossiya-Yanvar-2018-PDF.torrent"
        # file_name = "Red.Hot.Chili.Peppers.The.Getaway.2016.MP3.torrent"
        file_name = "10756_Music_Of_India.torrent"
        # file_name = "Мумий тролль.torrent"
        # file_name = "rutor.isevro_hit_top_40_europa_plus_02.02.2018.torrent"
        # loader = Loader(os.path.abspath("samples\\" + file_name),
        #                os.path.abspath("results\\"))
        # loader.download()
        file_name = "samples\\" + file_name
        self.add_torrent([None, file_name])


if __name__ == "__main__":
    ConsoleInterface().start()


