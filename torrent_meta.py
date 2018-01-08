class TorrentMeta:
    def __init__(self, bencode_source):
        self.announce = bencode_source["announce"]
        self.info = bencode_source["info"]

        self.announce_list = [self.announce]
        self.creation_date = None
        self.comment = None
        self.created_by = None

        if "announce-list" in bencode_source.keys():
            self.announce_list += bencode_source["announce-list"]
        if "creation date" in bencode_source.keys():
            self.creation_date = bencode_source["creation date"]
        if "comment" in bencode_source.keys():
            self.comment = bencode_source["comment"]
        if "created by" in bencode_source.keys():
            self.created_by = bencode_source["created by"]

        self.name = self.info["name"]
        self.piece_length = self.info["piece length"]
        self.pieces = self.info["pieces"]

        self.private = None
        self.md5sum = None
        if "private" in self.info.keys():
            self.private = self.info["private"]
        if "md5sum" in self.info.keys():
            self.md5sum = self.info["md5sum"]

        self.file_name = None
        self.dir_name = None
        self.length = None
        self.files = None

        if "length" in self.info.keys():
            self.file_name = self.info["name"]
            self.length = self.info["length"]
        else:
            self.dir_name = self.info["name"]
            self.files = []
            for record in self.info["files"]:
                self.files.append()
