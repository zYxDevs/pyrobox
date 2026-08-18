import sys
import subprocess

def get_gpu_names():
    gpus = set()

    if sys.platform.startswith('win'):
        import ctypes
        from ctypes import wintypes

        class DISPLAY_DEVICEW(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("DeviceName", ctypes.c_wchar * 32),
                ("DeviceString", ctypes.c_wchar * 128),
                ("StateFlags", wintypes.DWORD),
                ("DeviceID", ctypes.c_wchar * 128),
                ("DeviceKey", ctypes.c_wchar * 128)
            ]

        user32 = ctypes.windll.user32
        disp_dev = DISPLAY_DEVICEW()
        disp_dev.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        
        dev_num = 0
        while user32.EnumDisplayDevicesW(None, dev_num, ctypes.byref(disp_dev), 0):
            gpu_name = disp_dev.DeviceString
            if gpu_name:
                gpus.add(gpu_name.lower())
            dev_num += 1

    elif sys.platform.startswith('linux'):
        try:
            # lspci lists all PCI devices. We filter for VGA (graphics) or 3D controllers.
            output = subprocess.check_output(['lspci'], text=True)
            for line in output.splitlines():
                if 'VGA compatible controller' in line or '3D controller' in line:
                    # Output looks like: "01:00.0 VGA compatible controller: NVIDIA Corporation GA106 [GeForce RTX 3060]"
                    # We split by ':' and take the last part.
                    gpu_name = line.split(':')[-1].strip()
                    gpus.add(gpu_name.lower())
        except (FileNotFoundError, subprocess.SubprocessError):
            pass

    return list(gpus)

# E.g., ['nvidia corporation ga106 [geforce rtx 3060]']