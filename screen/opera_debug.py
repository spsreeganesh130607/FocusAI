import win32gui
import win32process
import psutil


window = win32gui.GetForegroundWindow()

title = win32gui.GetWindowText(window)

_, pid = win32process.GetWindowThreadProcessId(window)

process = psutil.Process(pid)

print("Foreground window:")
print("------------------")
print("PID:", pid)
print("Process:", process.name())
print("Title:", title)