from pathlib import Path
import json
import shutil

from file_manager import organizer_impl as organizer

base = Path('tmp_png_test')
src = base / 'src'
target = base / 'target'
if base.exists():
    shutil.rmtree(base)
src.mkdir(parents=True)
target.mkdir(parents=True)

# create sample files
(src / 'a.png').write_bytes(b'PNGDATA')
(src / 'b.png').write_bytes(b'PNG2')
(src / 'c.txt').write_text('plain text')

files = []
for p in src.iterdir():
    if p.is_file():
        files.append({'path': str(p), 'ext': p.suffix.lstrip('.'), 'size': p.stat().st_size, 'ctime': p.stat().st_ctime, 'mtime': p.stat().st_mtime})

print('Running organize_by_type dry-run extensions=["png"]')
actions = organizer.organize_by_type(files, target, dry_run=True, mode='move', extensions=['png'])
print(json.dumps(actions, indent=2))

print('\nDry-run complete. Inspect tmp_png_test directory if needed.')
