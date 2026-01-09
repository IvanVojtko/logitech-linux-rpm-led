from wheels.protocols import HIDClassic
from wheels.protocols import HIDpp

class G29(HIDClassic):
    PRODUCT_IDS = (0xC24F, 0xC260)   # PS3 / PS4 variants

class G923xbox(HIDpp):
    PRODUCT_IDS = [0xC26E]   # Xbox variant

class G923ps4(HIDClassic):
    PRODUCT_IDS = [0xC267]   # PS4 variant
