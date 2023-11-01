import socket
import struct

PACKET_ID_POS = 5
REV_PERCENT_POS = 8
CAR_TELEMETRY_ID = 6
BUFFER_SIZE = 1352


class F12023:
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

    def get_rpm_percent(self, data, prev_value) -> int:
        # Define the struct format for PacketHeader
        packet_header_format = '<HBBBBBQfIIBB'
        
        # Define the struct format for CarTelemetryData
        car_telemetry_format = '<HfffBbHBBH4H4B4BH4F4B'
        
        # Calculate the expected size of a single CarTelemetryData
        car_telemetry_size = struct.calcsize(car_telemetry_format)
        
        if len(data) >= struct.calcsize(packet_header_format):
            header_data = struct.unpack(packet_header_format, data[:struct.calcsize(packet_header_format)])
            packet_id = header_data[PACKET_ID_POS]  # The 10th element is m_packetId

            if packet_id == CAR_TELEMETRY_ID:
                telemetry_data = data[struct.calcsize(packet_header_format):]
                num_cars = len(telemetry_data) // car_telemetry_size  # Calculate the number of cars in the packet

                if num_cars > 0:
                    rev_lights_percent = struct.unpack(car_telemetry_format, telemetry_data[:car_telemetry_size])[REV_PERCENT_POS]
                    return rev_lights_percent
        return prev_value
        