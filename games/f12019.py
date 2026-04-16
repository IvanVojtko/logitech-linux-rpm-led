import socket
import struct

PACKET_ID_POS = 4
PLAYER_CAR_INDEX_POS = 8
REV_PERCENT_POS = 8
CAR_TELEMETRY_ID = 6
BUFFER_SIZE = 1347
PACKET_HEADER = struct.Struct("<HBBBBQfIB")
PACKET_HEADER_SIZE = PACKET_HEADER.size
CAR_TELEMETRY = struct.Struct("<HfffBbHBB4H4H4H4H4f4B")
CAR_TELEMETRY_SIZE = CAR_TELEMETRY.size


class F12019:
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
        if len(data) < PACKET_HEADER_SIZE:
            return prev_value
        header_data = PACKET_HEADER.unpack_from(data)
        if header_data[PACKET_ID_POS] != CAR_TELEMETRY_ID:
            return prev_value

        telemetry_length = len(data) - PACKET_HEADER_SIZE
        num_cars = telemetry_length // CAR_TELEMETRY_SIZE
        if num_cars <= 0:
            return prev_value

        player_car_index = header_data[PLAYER_CAR_INDEX_POS]
        if not (0 <= player_car_index < num_cars):
            return prev_value
        player_data_pos = PACKET_HEADER_SIZE + player_car_index * CAR_TELEMETRY_SIZE
        if len(data) < player_data_pos + CAR_TELEMETRY_SIZE:
            return prev_value
        rev_lights_percent = CAR_TELEMETRY.unpack_from(data, player_data_pos)[REV_PERCENT_POS]
        return rev_lights_percent

        
