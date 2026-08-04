import win32security

share_name = "dummy"
server = "localhost"

target1 = share_name
target2 = f"\\\\{server}\\{share_name}"

print("SE_LMSHARE:", win32security.SE_LMSHARE)
