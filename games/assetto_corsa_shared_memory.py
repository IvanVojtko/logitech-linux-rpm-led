import struct
import mmap
import sys
import os

CURR_POS = 5
MAX_POS = 12
# ACR_PHYSICS_MAX_POS = 62

PHYSICS_TELEMETRY =     struct.Struct("<ifffiiff 3f3f 4f4f4f4f4f4f4f4f4f ffffff 5f iifffi 2f fffff 3f ff iiiiiiii 4f f 4f4f4f i 12f12f12f f 3f ii i 4f4f4f4f4fii4f4fii4f4ff4fii4f4fii ffff")
# ACR_PHYSICS_TELEMETRY = struct.Struct("<ifffiiff 3f3f 4f4f4f4f4f4f4f4f4f ffffff 5f iifffi 2f fffff 3f ff iiiiiiii 4f f 4f4f4f i 12f12f12f f 3f ii f 4f4f4f4f4fii4f4fii4f4ff4fii4f4fii i ffff")
PHYSICS_SIZE = PHYSICS_TELEMETRY.size
# ACR_PHYSICS_SIZE = ACR_PHYSICS_TELEMETRY.size
STATIC_TELEMETRY = struct.Struct("30s30sii66s66s66s66s66siffif4f4ffffifffifiiiiifiif66sfii66siiii66s66s")
STATIC_SIZE = STATIC_TELEMETRY.size
BLINKING_TICKS = 2

class AssettoCorsaSharedMemory:
    def __init__(self, max_rpm = 0):
        self.max_rpm = max_rpm
        self.mmap_physics = None
        self.mmap_static = None

    def connect(self):
        if sys.platform == "win32":
            self.mmap_physics = mmap.mmap(-1, PHYSICS_SIZE, tagname="Local\\acpmf_physics", access=mmap.ACCESS_WRITE)
            self.mmap_static = mmap.mmap(-1, STATIC_SIZE, "Local\\acpmf_static", access=mmap.ACCESS_READ)
        else:
            self.mmap_physics = AssettoCorsaSharedMemory._load_linux_shm("acpmf_physics", PHYSICS_SIZE)
            self.mmap_static = AssettoCorsaSharedMemory._load_linux_shm("acpmf_static", STATIC_SIZE)
        if self.mmap_physics is None or self.mmap_static is None:
            raise Exception('Unable to open shared memory. It may not be initialized yet.')
    
    @staticmethod
    def _load_linux_shm(shared_mem: str, size: int):
        if os.path.isdir('/dev/shm/'):
            try:
                with open('/dev/shm/%s' % shared_mem, 'r+b') as f:
                    return mmap.mmap(f.fileno(), size, access=mmap.ACCESS_READ)
            except:
                try:
                    # Steam Flatpak variant adds shared memory to a "flatpak-com.valvesoftware.Steam-AAAAAA" directory,
                    # so we search inside sub-directories
                    for directory in os.listdir('/dev/shm/'):
                        try:
                            with open('/dev/shm/%s/%s' % (directory, shared_mem), 'r+b') as f:
                                return mmap.mmap(f.fileno(), size, access=mmap.ACCESS_READ)
                        except OSError:
                            pass
                except Exception as exc:
                    print("ERROR: Could not open memory location")
                    raise exc
        else:
            return None

    def disconnect(self):
        if self.mmap_physics:
            self.mmap_physics.close()
        if self.mmap_static:
            self.mmap_static.close()

        self.mmap_physics = None
        self.mmap_static = None

    def read_data(self):
        self.mmap_physics.seek(0)
        physics_data = self.mmap_physics.read(PHYSICS_SIZE)
        self.mmap_static.seek(0)
        static_data = self.mmap_static.read(STATIC_SIZE)
        
        return [physics_data, static_data]

    def get_rpm_percent(self, data, prev_value) -> int:
        if (data is None):
            print("Warning: data is None")
            return prev_value

        if len(data[0]) < PHYSICS_SIZE or len(data[1]) < STATIC_SIZE:
            print("Warning: data is not long enough")
            return prev_value
        
        current_rpm = PHYSICS_TELEMETRY.unpack_from(data[0])[CURR_POS]
        # print(f"RPM: {current_rpm}")

        if self.max_rpm != 0:
            max_rpm = self.max_rpm
        else:
            max_rpm = STATIC_TELEMETRY.unpack_from(data[1])[MAX_POS]
            # max_rpm = ACR_PHYSICS_TELEMETRY.unpack_from(data[0])[ACR_PHYSICS_MAX_POS]
        # print(f"Max RPM: {max_rpm}")

        if current_rpm <= 0:
            return 0
        if max_rpm <= 0:
            return prev_value
        rpm_percent = int((current_rpm / max_rpm) * 100)

        # When RPM is at high RPM, add a blinking effect for a few ticks
        if rpm_percent >= 98 and prev_value >= 90:
            return 0
        # manipulate prev_value as an increment using very low value compared to current RPM
        if rpm_percent >= 90 and prev_value < BLINKING_TICKS:
            return prev_value + 1

        return rpm_percent
