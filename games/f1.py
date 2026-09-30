import socket
import struct

CAR_TELEMETRY_ID = 6
REV_PERCENT_POS = 8


class F1Telemetry:
    """Codemasters F1 car telemetry. The seasons differ only in packet layout.

    Sub-classes must provide:
    PACKET_HEADER:        struct.Struct
    PACKET_ID_POS:        int, index of packetId in the unpacked header
    PLAYER_CAR_INDEX_POS: int, index of playerCarIndex in the unpacked header
    CAR_TELEMETRY:        struct.Struct, one car's entry in the car array
    BUFFER_SIZE:          int, size of the whole car telemetry packet
    """
    PACKET_HEADER: struct.Struct
    PACKET_ID_POS: int
    PLAYER_CAR_INDEX_POS: int
    CAR_TELEMETRY: struct.Struct
    BUFFER_SIZE: int

    def __init__(self):
        self.ip = "127.0.0.1"
        self.port = 20777

    def connect(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((self.ip, self.port))
        return udp_socket

    def read_data(self, udp_socket):
        data, addr = udp_socket.recvfrom(self.BUFFER_SIZE)
        return data

    def get_rpm_percent(self, data, prev_value) -> int:
        header_size = self.PACKET_HEADER.size
        car_size = self.CAR_TELEMETRY.size
        if len(data) < header_size:
            return prev_value
        header_data = self.PACKET_HEADER.unpack_from(data)
        if header_data[self.PACKET_ID_POS] != CAR_TELEMETRY_ID:
            return prev_value

        telemetry_length = len(data) - header_size
        num_cars = telemetry_length // car_size
        if num_cars <= 0:
            return prev_value

        player_car_index = header_data[self.PLAYER_CAR_INDEX_POS]
        if not (0 <= player_car_index < num_cars):
            return prev_value
        player_data_pos = header_size + player_car_index * car_size
        if len(data) < player_data_pos + car_size:
            return prev_value
        rev_lights_percent = self.CAR_TELEMETRY.unpack_from(data, player_data_pos)[REV_PERCENT_POS]
        return rev_lights_percent


class F12019(F1Telemetry):
    PACKET_HEADER = struct.Struct("<HBBBBQfIB")
    PACKET_ID_POS = 4
    PLAYER_CAR_INDEX_POS = 8
    CAR_TELEMETRY = struct.Struct("<HfffBbHBB4H4H4HH4f4B")
    BUFFER_SIZE = 1347


class F12020(F1Telemetry):
    # The header gained secondaryPlayerCarIndex and the tyre temperatures
    # shrank to uint8.
    PACKET_HEADER = struct.Struct("<HBBBBQfIBB")
    PACKET_ID_POS = 4
    PLAYER_CAR_INDEX_POS = 8
    CAR_TELEMETRY = struct.Struct("<HfffBbHBB4H4B4BH4f4B")
    BUFFER_SIZE = 1307


class F12022(F1Telemetry):
    PACKET_HEADER = struct.Struct("<HBBBBQfIBB")
    PACKET_ID_POS = 4
    PLAYER_CAR_INDEX_POS = 8
    # Tyre surface/inner temperatures are uint8 arrays, not uint16: the struct has to
    # come out at 60 bytes, matching BUFFER_SIZE (24 header + 22 * 60 + 3 trailing).
    CAR_TELEMETRY = struct.Struct("<HfffBbHBBH4H4B4BH4f4B")
    BUFFER_SIZE = 1347


class F12023(F1Telemetry):
    # Only the packet header changed from F1 22.
    PACKET_HEADER = struct.Struct("<HBBBBBQfIIBB")
    PACKET_ID_POS = 5
    PLAYER_CAR_INDEX_POS = 10
    CAR_TELEMETRY = F12022.CAR_TELEMETRY
    BUFFER_SIZE = 1352
