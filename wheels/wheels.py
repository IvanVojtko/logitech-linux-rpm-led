from wheels.protocols import HIDClassic
from wheels.protocols import HIDpp

class G27(HIDClassic):
    PRODUCT_IDS = (0xC294, 0xC29B)   # Driving Force Compatibility/Native variant

class G29(HIDClassic):
    PRODUCT_IDS = (0xC24F, 0xC260)   # PS3 / PS4 variants

class G923xbox(HIDpp):
    PRODUCT_IDS = (0xC26E, 0xC266)   # Xbox variant

class G923ps4(HIDClassic):
    PRODUCT_IDS = [0xC267]   # PS4 variant

# UNTESTED!
class GPROxbox(HIDpp):
    PRODUCT_IDS = [0xC268]   # Xbox variant

# UNTESTED!
class GPROps4(HIDClassic):
    PRODUCT_IDS = [0xC272]   # PS4 variant

# UNTESTED!
class RS50(HIDpp):
    PRODUCT_IDS = [0xC276]
