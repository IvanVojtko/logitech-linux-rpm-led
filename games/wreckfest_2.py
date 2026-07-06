import socket
import struct

import time
import struct

MAX_POS = 63
CURR_POS = 37
BUFFER_SIZE = 2048
CAR_TELEMETRY = struct.Struct('<66f')
CAR_TELEMETRY_SIZE = CAR_TELEMETRY.size


class Wreckfest2:
    def __init__(self):
        self.ip = "127.0.0.1"
        self.port = 23123
        self.rpm = 0
        self.rpmMax = 1
        
    def connect(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((self.ip, self.port))
        return udp_socket
        
    def read_data(self, udp_socket):
        data, addr = udp_socket.recvfrom(BUFFER_SIZE)
        return data
    
    def calc_rpm_percent(self):
        if (self.rpmMax == 0):
            return 0

        rpm_percent = (self.rpm * 100) / self.rpmMax
        # Return 0 if rpm is 99 or above to have a blinking effect when reaching max RPM
        if (rpm_percent >= 99):
            return 0
        return rpm_percent

    def get_rpm_percent(self, data, percent) -> int:
        signature = int.from_bytes(data[0:4], byteorder='little', signed=False)
        packetType = int.from_bytes(data[4:5], byteorder='little', signed=False)
        if signature != 1869769584:
            print ("ERROR: Invalid packet signature")
            return percent
        
        if packetType != 0:
            return percent

        self.rpm = int.from_bytes(data[435:439], byteorder='little', signed=True)# S32
        self.rpmMax = int.from_bytes(data[439:443], byteorder='little', signed=True)# S32
        # print("rpm: ", self.rpm)
        # print("rpmMax: ", self.rpmMax)
        # print("rpm ratio: ", self.calc_rpm_percent())

        return self.calc_rpm_percent()
