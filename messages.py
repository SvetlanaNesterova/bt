def int_to_four_bytes_big_endian(number):
    return number.to_bytes(4, byteorder='big')


def bytes_to_int(_bytes):
    return int.from_bytes(_bytes, byteorder='big')


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

    length = int_to_four_bytes_big_endian(2**14)

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

