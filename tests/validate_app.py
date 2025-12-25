import shutil
from pathlib import Path
import sys
# Ensure project root is on sys.path so `file_manager` package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import file_manager.organizer as organizer
import json
import sys

ROOT = Path('tmp_validation')
if ROOT.exists():
    shutil.rmtree(ROOT)
ROOT.mkdir()

src = ROOT / 'src'
src.mkdir()
# create files
(f1 := src / 'a.txt').write_text('hello')
(f2 := src / 'b.bin').write_bytes(b'\x00' * 2048)

files = [{'path': str(f1), 'ext': 'txt'}, {'path': str(f2), 'ext': 'bin'}]

target = ROOT / 'target'
print('Running organize_by_type with copy mode')
actions = organizer.organize_by_type(files, target, dry_run=False, mode='copy')
print('Actions len:', len(actions))
# find log
logp = None
if actions and isinstance(actions[-1], dict) and 'log' in actions[-1]:
    logp = Path(actions[-1]['log'])
    print('Log written to', logp)
else:
    print('No log found')

# verify copies exist
copied = [a for a in actions if isinstance(a, dict) and a.get('status') == 'copied']
print('Copied actions:', len(copied))
for c in copied:
    dst = Path(c['dst'])
    print('Exists?', dst, dst.exists())
    if not dst.exists():
        print('ERROR: copied dst missing', dst)
        sys.exit(2)

print('Running undo_moves on log (should delete copies)')
if logp:
    res = organizer.undo_moves(logp, dry_run=False)
    print('Undo results sample:', res[:5])
    # ensure dst no longer exists
    for c in copied:
        dst = Path(c['dst'])
        print('Post-undo exists?', dst, dst.exists())
        if dst.exists():
            print('ERROR: dst still exists after undo', dst)
            sys.exit(3)
else:
    print('No log to undo')

# now test move mode
# recreate source files
(f1 := src / 'a2.txt').write_text('world')
(f2 := src / 'b2.bin').write_bytes(b'\x11' * 1024)
files2 = [{'path': str(f1), 'ext': 'txt'}, {'path': str(f2), 'ext': 'bin'}]
print('Running organize_by_type with move mode')
actions2 = organizer.organize_by_type(files2, target, dry_run=False, mode='move')
print('Actions2 len:', len(actions2))
logp2 = None
if actions2 and isinstance(actions2[-1], dict) and 'log' in actions2[-1]:
    logp2 = Path(actions2[-1]['log'])
    print('Log2', logp2)

moved = [a for a in actions2 if isinstance(a, dict) and a.get('status') == 'moved']
for m in moved:
    dst = Path(m['dst'])
    print('Moved exists?', dst, dst.exists())
    if not dst.exists():
        print('ERROR: moved dst missing', dst)
        sys.exit(4)

print('Undoing move log (should restore original files)')
if logp2:
    res2 = organizer.undo_moves(logp2, dry_run=False)
    print('Undo2 results sample:', res2[:5])
    for m in moved:
        dst = Path(m['dst'])
        print('After undo exists?', dst, dst.exists())
        # original src restored to restored filename; dst should no longer exist
        if dst.exists():
            print('ERROR: moved dst still exists after undo', dst)
            sys.exit(5)

print('CLEANUP: removing', ROOT)
shutil.rmtree(ROOT)
print('ALL TESTS PASSED')
