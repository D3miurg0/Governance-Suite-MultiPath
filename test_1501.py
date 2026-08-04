import win32net

try:
    info = {"security_descriptor": None}
    win32net.NetShareSetInfo(None, "dummy", 1501, info)
    print("1501 accepted (even if it fails with access denied)")
except ValueError as e:
    print("ValueError:", e)
except Exception as e:
    print("Exception:", type(e).__name__, e)
