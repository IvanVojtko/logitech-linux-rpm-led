import socket
from struct import unpack

MAX_POS = 49
CURR_POS = 48
BUFFER_SIZE = 2048


class Automobilista2:
    def __init__(self):
        self.ip = "0.0.0.0"
        self.port = 5606
        self.packet_string = self.get_packet_string()
        
    def connect(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((self.ip, self.port))
        print("Connected")
        return udp_socket
        
    def read_data(self, udp_socket):
        data, addr = udp_socket.recvfrom(BUFFER_SIZE)
        return data
    
    def get_rpm_percent(self, data, percent) -> int:
        # not a telemetry packet. Return previous percent
        if len(data) != 1367:
            return percent
        
        telemetry_data = unpack(self.packet_string, data)
        current_rpm = int(telemetry_data[CURR_POS])
        max_rpm = int(telemetry_data[MAX_POS])

        if max_rpm == 0 or current_rpm == 0:
            return percent
        return int((current_rpm / max_rpm) * 100)
    
    def get_packet_string(self):
        packet_string = "HB"
        packet_string += "B"
        packet_string += "bb"
        packet_string += "BBbBB"
        packet_string += "B"
        packet_string += "21f"
        packet_string += "H"
        packet_string += "B"
        packet_string += "B"
        packet_string += "hHhHHBBBBBbffHHBBbB"
        packet_string += "22f"
        packet_string += "8B12f8B8f12B4h20H16f4H"
        packet_string += "2f"
        packet_string += "2B"
        packet_string += "bbBbbb"

        packet_string += "hhhHBBBBf"*56

        packet_string += "fBBB"

        return packet_string