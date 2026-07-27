from wheels.protocols import HIDClassic
from wheels.protocols import HIDpp

class G27(HIDClassic):
    PRODUCT_IDS = (0xC294, 0xC29B)   # Driving Force Compatibility/Native variant

class G29(HIDClassic):
    PRODUCT_IDS = (0xC24F, 0xC260)   # PS3 / PS4 variants

class G923xbox(HIDpp):
    PRODUCT_IDS = [0xC26E]   # Xbox variant

class G923ps(HIDClassic):
    # PlayStation variant: 0xC266 is PC (native) mode, 0xC267 is PS4 mode.
    # Both drive the rev lights with the classic 0xF8 0x12 report, like the G29.
    PRODUCT_IDS = (0xC266, 0xC267)

# UNTESTED!
class GPROxbox(HIDpp):
    PRODUCT_IDS = [0xC268]   # Xbox variant

# UNTESTED!
class GPROps4(HIDClassic):
    PRODUCT_IDS = [0xC272]   # PS4 variant

# UNTESTED!
class RS50(HIDpp):
    PRODUCT_IDS = [0xC276]
