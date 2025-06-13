def _load_constant_from_file(filepath):
    with open(filepath, "r") as f:
        return float(f.readline())
    
END_DEVICE_LAT = _load_constant_from_file("configs/.latitude")
END_DEVICE_LON = _load_constant_from_file("configs/.longitude")