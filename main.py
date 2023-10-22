from games.forza_horizon import ForzaHorizon5, MAX_POS, CURR_POS
from wheels.g29 import G29

horizon = ForzaHorizon5()
udp_socket = horizon.connect()
wheel = G29()
wheel.connect()

while True:
    data = horizon.read_data(udp_socket=udp_socket)
    max_rpm, current_rpm = horizon.parse_rpm(data=data)
    
    if max_rpm != 0 and current_rpm != 0:
        percent = horizon.get_rpm_percent(current_rpm=current_rpm, max_rpm=max_rpm)
        wheel.leds_rpm(percent)
    else:
        wheel.leds_rpm(0)
