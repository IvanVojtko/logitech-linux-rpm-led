import socket
import struct

PACKET_ID_POS = 4	    #Same in 2019, 2020, 2022
REV_PERCENT_POS = 8	    #Same in 2019 & 2020
CAR_TELEMETRY_ID = 6	#Same in 2019, 2020, 2022
BUFFER_SIZE = 1347	    #1347 in 2019, 1307 in 2020, 1347 in 2022


class F12022:
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
        packet_header_format = "<HBBBBQfIBB"                #2020 spec added an extra header - uint8     m_secondaryPlayerCarIndex;  - Index of secondary player's car in the array (splitscreen) - 255 if no second player - No change from 2020 to 2022

        # Define the struct format for CarTelemetryData
        car_telemetry_format = "<HfffBbHBBH4H4H4HH4f4B"     #Change 2020 to 2022 spec added an extra item to the telemetry stream: uint16    m_revLightsBitValue;        // Rev lights (bit 0 = leftmost LED, bit 14 = rightmost LED)
        
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
