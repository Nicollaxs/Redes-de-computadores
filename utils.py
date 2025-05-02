import hashlib
import struct
import random

# Probabilidades (podem ser configuradas no seu código principal)
LOSS_PROB = 0.1
CORRUPTION_PROB = 0.1

class RDTPacket:
    def __init__(self, seq_num, data, checksum):
        self.seq_num = seq_num
        self.data = data
        self.checksum = checksum

def make_packet(seq_num, data):
    checksum = hashlib.md5(data).hexdigest()
    header = struct.pack('!I', seq_num) + checksum.encode()
    return header + data

def unpack_packet(packet):
    try:
        seq_num = struct.unpack('!I', packet[:4])[0]
        checksum = packet[4:36].decode()
        data = packet[36:]
        return RDTPacket(seq_num, data, checksum)
    except Exception:
        return None

def is_corrupted(packet):
    return hashlib.md5(packet.data).hexdigest() != packet.checksum

def simulate_loss():
    return random.random() < LOSS_PROB

def simulate_corruption():
    return random.random() < CORRUPTION_PROB
