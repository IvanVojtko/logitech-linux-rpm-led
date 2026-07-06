import socket
import struct

CURR_POS = 435
MAX_POS = 439
BUFFER_SIZE = 2048

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
        packetType = data[4]
        if signature != 1869769584:
            print ("ERROR: Invalid packet signature")
            return percent
        
        if packetType != 0:
            return percent
        
        if len(data) < MAX_POS + 4:
            print ("ERROR: Packet was too small, cannot extract RPM")
            return percent

        self.rpm = int.from_bytes(data[CURR_POS:CURR_POS + 4], byteorder='little', signed=True)# S32
        self.rpmMax = int.from_bytes(data[MAX_POS:MAX_POS + 4], byteorder='little', signed=True)# S32
        # print("rpm: ", self.rpm)
        # print("rpmMax: ", self.rpmMax)
        # print("rpm %: ", self.calc_rpm_percent())

        return self.calc_rpm_percent()
