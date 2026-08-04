import win32net
import win32security
import ntsecuritycon

# create dummy folder
import os
os.makedirs("C:\\Temp\\testshare", exist_ok=True)

share_name = "TestSharePerms"

# try delete if exists
try:
    win32net.NetShareDel(None, share_name)
except:
    pass

# create share
info = {
    "netname": share_name,
    "path": "C:\\Temp\\testshare",
    "remark": "test",
    "max_uses": -1,
    "type": 0
}
win32net.NetShareAdd(None, 2, info)

# change permission using SetNamedSecurityInfo to something unique
everyone, domain, type = win32security.LookupAccountName(None, "Everyone")
sd = win32security.GetNamedSecurityInfo(
    share_name, win32security.SE_LMSHARE, win32security.DACL_SECURITY_INFORMATION
)
dacl = sd.GetSecurityDescriptorDacl()
# clear dacl
dacl = win32security.ACL()
# add everyone read
dacl.AddAccessAllowedAce(win32security.ACL_REVISION, ntsecuritycon.GENERIC_READ, everyone)
sd.SetSecurityDescriptorDacl(1, dacl, 0)
win32security.SetNamedSecurityInfo(
    share_name, win32security.SE_LMSHARE, win32security.DACL_SECURITY_INFORMATION, None, None, dacl, None
)

print("Original SD applied")
full = win32net.NetShareGetInfo(None, share_name, 502)
sd_backup = full.get("security_descriptor")

# recreate
win32net.NetShareDel(None, share_name)
win32net.NetShareAdd(None, 2, info)

# apply via NetShareSetInfo 502
full2 = win32net.NetShareGetInfo(None, share_name, 502)
full2["security_descriptor"] = sd_backup
win32net.NetShareSetInfo(None, share_name, 502, full2)

# read back
full3 = win32net.NetShareGetInfo(None, share_name, 502)
sd_new = full3.get("security_descriptor")
dacl_new = sd_new.GetSecurityDescriptorDacl()

print("Restored ACE count:", dacl_new.GetAceCount())

win32net.NetShareDel(None, share_name)
