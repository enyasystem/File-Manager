from pathlib import Path
import importlib
from file_manager import scanner
import file_manager.organizer_impl as impl
importlib.reload(impl)

src = r"C:\Users\Enyasystem\Downloads"
tgt = Path(r"C:\Users\Enyasystem\Desktop\fm_test_target")

items = []
for it in scanner.scan_paths([src], recursive=True):
    items.append(it)
print('scanned items:', len(items))
actions = impl.organize_by_type(items, tgt, dry_run=True, mode='move', extensions=['png'])
print('actions:', len(actions))
for a in actions[:30]:
    print(a)
