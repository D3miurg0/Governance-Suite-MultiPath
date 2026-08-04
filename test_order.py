import win32net
try:
    print("Testing (server, client, user, level)")
    res = win32net.NetSessionEnum(None, None, None, 10)
    print("Success:", res)
except Exception as e:
    print("Failed:", type(e).__name__, e)

try:
    print("Testing (level, server, client, user)")
    res = win32net.NetSessionEnum(10, None, None, None)
    print("Success:", res)
except Exception as e:
    print("Failed:", type(e).__name__, e)

try:
    print("Testing with server name string")
    res = win32net.NetSessionEnum("localhost", None, None, 10)
    print("Success:", res)
except Exception as e:
    print("Failed:", type(e).__name__, e)

try:
    print("Testing with server name string as 2nd arg")
    res = win32net.NetSessionEnum(10, "localhost", None, None)
    print("Success:", res)
except Exception as e:
    print("Failed:", type(e).__name__, e)
