import win32net
import itertools

elements = ["", "127.0.0.1", 10, None]
args_lists = []
for i in range(1, 5):
    for combo in itertools.product(elements, repeat=i):
        args_lists.append(combo)

for args in args_lists:
    try:
        res = win32net.NetSessionEnum(*args)
        print(f"SUCCESS with args: {args}")
    except TypeError as e:
        pass
    except Exception as e:
        pass
