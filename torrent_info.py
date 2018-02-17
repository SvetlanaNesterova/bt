import hashlib
from bencode import BencodeTranslator


class TorrentMeta:
    def __init__(self, bencode_source):
        self._announce = bencode_source[b"announce"]
        self._info = bencode_source[b"info"]
        self.info_hash = self._calc_info_hash()

        self.announce_list = [self._announce]
        self.creation_date = None
        self.comment = None
        self.created_by = None

        if b"announce-list" in bencode_source.keys():
            self.announce_list += [record[0] for record in
                                   bencode_source[b"announce-list"]]
        if b"creation date" in bencode_source.keys():
            self.creation_date = bencode_source[b"creation date"]
        if b"comment" in bencode_source.keys():
            self.comment = bencode_source[b"comment"]
        if b"created by" in bencode_source.keys():
            self.created_by = bencode_source[b"created by"]

        self.piece_length = self._info[b"piece length"]
        self.pieces_hashes = [
            self._info[b"pieces"][piece_index:piece_index + 20]
            for piece_index in range(0, len(self._info[b"pieces"]), 20)]

        self.private = None
        self.md5sum = None
        if b"private" in self._info.keys():
            self.private = self._info[b"private"]
        if b"md5sum" in self._info.keys():
            self.md5sum = self._info[b"md5sum"]

        self.is_one_file = False
        self.is_many_files = False

        self.file_name = None
        self.dir_name = None
        self.length = None
        self.files = None

        if b"length" in self._info.keys():
            self.is_one_file = True
            self.file_name = self._info[b"name"]
            self.length = self._info[b"length"]
            self.dir_name = b""
            self.files = [FileRecord(
                {b"length": self.length, b"path": [self.file_name]}, 0)]
        else:
            self.is_many_files = True
            ### ?????????????
            self.dir_name = b"\\" + self._info[b"name"]
            self.length = 0
            self.files = []
            for record in self._info[b"files"]:
                self.files.append(FileRecord(record, self.length))
                self.length += self.files[-1].length

    def _calc_info_hash(self):
        info_bencode = BencodeTranslator.translate_to_bencode(self._info)
        return get_sha_1_hash(info_bencode)


class FileRecord:
    def __init__(self, record: dict, offset):
        self.length = record[b"length"]
        self.path = record[b"path"]
        self.offset = offset
        if b"md5sum" in record.keys():
            self.md5sum = record[b"md5sum"]
        else:
            self.md5sum = None


def int_to_four_bytes_big_endian(number):
    return number.to_bytes(4, byteorder='big')


def bytes_to_int(_bytes):
    return int.from_bytes(_bytes, byteorder='big')


def get_sha_1_hash(source):
    hasher = hashlib.sha1()
    hasher.update(source)
    return hasher.digest()


class Messages:
    choke = b'\0'
    unchoke = b'\1'
    interested = b'\2'
    not_interested = b'\3'
    have = b'\4'
    bitfield = b'\5'
    request = b'\6'
    piece = b'\7'
    cancel = b'\x08'

    piece_segment_length = 2 ** 14

    """
    b'\0': 'choke',
    b'\1': 'unchoke',
    b'\2': 'interested',
    b'\3': 'not_interested',
    b'\4': 'have',
    b'\5': 'bitfield',
    b'\6': 'request',
    b'\7': 'piece',
    b'\x08': 'cancel'
    """

    messages_types = {
        0: 'choke',
        1: 'unchoke',
        2: 'interested',
        3: 'not_interested',
        4: 'have',
        5: 'bitfield',
        6: 'request',
        7: 'piece',
        8: 'cancel'
    }
