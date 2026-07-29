import socket
import struct

PORT = 4444

CURR_POS = 6
# Packet format without the optional ID at the end
CAR_TELEMETRY = struct.Struct("<I4sH2c7f2I3f16s16s")
CAR_TELEMETRY_SIZE = CAR_TELEMETRY.size

class OutGauge:
    def __init__(self, max_rpm):
        self.ip = "127.0.0.1"
        self.port = PORT
        self.max_rpm = max(1.0, float(max_rpm))
        
    def connect(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((self.ip, self.port))
        return udp_socket
        
    def read_data(self, udp_socket):
        data, addr = udp_socket.recvfrom(CAR_TELEMETRY_SIZE)
        return data

    def get_rpm_percent(self, data, prev_value) -> int:
        if not data:
            print ("ERROR: Empty data")
            return prev_value

        if len(data) < CAR_TELEMETRY_SIZE:
            print("ERROR: Packet size is smaller than expected")
            return prev_value

        current_rpm = CAR_TELEMETRY.unpack_from(data)[CURR_POS]
        if current_rpm <= 0:
            return 0
        return int((current_rpm / self.max_rpm) * 100)
