import socket
import struct

MAX_POS = [8, 12]
CURR_POS = [16, 20]
BUFFER_SIZE = 323
RPM_PACKET_MIN_SIZE = CURR_POS[1]
FLOAT32_LE = struct.Struct('<f')


class ForzaHorizon5:
    def __init__(self):
        self.ip = "127.0.0.1"
        self.port = 5300
        
    def connect(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((self.ip, self.port))
        return udp_socket
        
    def read_data(self, udp_socket):
        data, addr = udp_socket.recvfrom(BUFFER_SIZE)
        return data
    
    def parse_rpm(self, data) -> tuple:
        if len(data) < RPM_PACKET_MIN_SIZE:
            return 0.0, 0.0
        max_rpm = FLOAT32_LE.unpack_from(data, MAX_POS[0])[0]
        current_rpm = FLOAT32_LE.unpack_from(data, CURR_POS[0])[0]
        return max_rpm, current_rpm
    
    def get_rpm_percent(self, max_rpm, current_rpm) -> int:
        if max_rpm == 0 or current_rpm == 0:
            return 0
        return int((current_rpm / max_rpm) * 100)
