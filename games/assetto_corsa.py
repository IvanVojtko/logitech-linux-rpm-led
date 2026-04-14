import socket
import struct

BUFFER_SIZE = 2048
PORT = 9996
HANDSHAKER = struct.Struct("<iii")
MESSAGE_SIZE = struct.Struct("<i")
FLOAT32_LE = struct.Struct("<f")

IDENTIFIER = 1
VERSION = 1
HANDSHAKE = 0
SUBSCRIBE_UPDATE = 1
DISMISS = 3

PACKET_IDENTIFIER = ord("a")
PACKET_SIZE_POS = 4
CURRENT_RPM_POS = 68
RPM_PACKET_MIN_SIZE = CURRENT_RPM_POS + FLOAT32_LE.size


class AssettoCorsa:
    def __init__(self, max_rpm):
        self.ip = "127.0.0.1"
        self.port = PORT
        self.max_rpm = max(1.0, float(max_rpm))

    def _send_operation(self, udp_socket, operation):
        udp_socket.send(HANDSHAKER.pack(IDENTIFIER, VERSION, operation))

    def connect(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.connect((self.ip, self.port))
        udp_socket.settimeout(1.0)

        self._send_operation(udp_socket, HANDSHAKE)
        try:
            udp_socket.recv(BUFFER_SIZE)
        except socket.timeout:
            pass

        self._send_operation(udp_socket, SUBSCRIBE_UPDATE)
        return udp_socket

    def disconnect(self, udp_socket):
        self._send_operation(udp_socket, DISMISS)

    def read_data(self, udp_socket):
        return udp_socket.recv(BUFFER_SIZE)

    def get_rpm_percent(self, data, prev_value) -> int:
        if len(data) < RPM_PACKET_MIN_SIZE:
            return prev_value
        if data[0] != PACKET_IDENTIFIER:
            return prev_value

        payload_size = MESSAGE_SIZE.unpack_from(data, PACKET_SIZE_POS)[0]
        if payload_size < RPM_PACKET_MIN_SIZE or payload_size > len(data):
            return prev_value

        current_rpm = FLOAT32_LE.unpack_from(data, CURRENT_RPM_POS)[0]
        if current_rpm <= 0:
            return 0
        return int((current_rpm / self.max_rpm) * 100)
