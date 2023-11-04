import socket
import struct

MAX_POS = 63
CURR_POS = 37
BUFFER_SIZE = 1024


class DirtRally2:
    def __init__(self):
        self.ip = "127.0.0.1"
        self.port = 20777
        
    def connect(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((self.ip, self.port))
        return udp_socket
        
    def read_data(self, udp_socket):
        data, addr = udp_socket.recvfrom(BUFFER_SIZE)
        return data
    
    def get_rpm_percent(self, data, percent) -> int:
        car_telemetry_size = struct.calcsize('<66f')
        game_data = struct.unpack('<66f', data[:car_telemetry_size])
        max_rpm = game_data[MAX_POS]
        current_rpm = game_data[CURR_POS]
        if max_rpm == 0 or current_rpm == 0:
            return percent
        return int((current_rpm / max_rpm) * 100)