import socket
import struct

BUFFER_SIZE = 64
PORT = 5607

PACKET_MAGIC = b"LRPM"
PACKET_VERSION = 1
PACKET_STRUCT = struct.Struct("<4sBBHff")


class EuroTruckSimulator2:
    def __init__(self):
        self.ip = "127.0.0.1"
        self.port = PORT

    def connect(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((self.ip, self.port))
        return udp_socket

    def read_data(self, udp_socket):
        data, _addr = udp_socket.recvfrom(BUFFER_SIZE)
        return data

    def get_rpm_percent(self, data, prev_value) -> int:
        if len(data) < PACKET_STRUCT.size:
            return prev_value

        magic, version, running, _reserved, current_rpm, max_rpm = PACKET_STRUCT.unpack_from(data)
        if magic != PACKET_MAGIC or version != PACKET_VERSION:
            return prev_value
        if not running:
            return 0
        if current_rpm <= 0:
            return 0
        if max_rpm <= 0:
            return prev_value
        return int((current_rpm / max_rpm) * 100)
