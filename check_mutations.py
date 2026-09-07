"""Exercise meaningful failures against isolated source copies; never contact USB."""

import json
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent
source = (root / 'transfer.py').read_text()
changes = {
    'baseline': (None, None),
    'comment only': ('# Recheck after backup', '# Check again after backup'),
    'skip validation': ('    if len(data) > MAX_FILE:', "    return Mission(1, '68', 'noAction')\n    if len(data) > MAX_FILE:"),
    'ignore aircraft mismatch': ('if previous.aircraft != mission.aircraft:', 'if False:'),
    'ignore missing remembered slot': ('        if remembered:', '        if False:'),
    'ignore exact storage': ("and s.storage_id == remembered.get('storage_id')", ''),
    'ignore simultaneous transfer': ('fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)', 'pass'),
    'skip durable backup': ('os.fsync(output.fileno())', 'pass'),
    'ignore controller edit': ('if backend.read(slot) != original:', 'if False:'),
    'ignore corrupt readback': ('if actual != incoming:', 'if False:'),
    'skip restoration': ("backend.write(slot, backup / 'original.kmz')", 'pass'),
    'ignore recovery pending': ("if receipt.get('status') in ('writing', 'recovery_needed'):", 'if False:'),
    'ignore backup checksum': ("if digest(expected) != receipt['original_sha256']:", 'if False:'),
}
report = {}
for name, (before, after) in changes.items():
    changed = source if before is None else source.replace(before, after)
    assert before is None or changed != source, name
    with tempfile.TemporaryDirectory(prefix='waypoint-mutation-') as directory:
        scratch = Path(directory)
        (scratch / 'transfer.py').write_text(changed)
        (scratch / 'test_transfer.py').write_text((root / 'test_transfer.py').read_text())
        process = subprocess.run(['/usr/bin/python3', '-B', '-m', 'unittest', '-q', 'test_transfer.py'],
                                 cwd=scratch, capture_output=True, text=True, timeout=20)
        report[name] = {'survived': process.returncode == 0,
                        'evidence': process.stderr[-2500:]}
        print(name, 'SURVIVED' if process.returncode == 0 else 'CAUGHT')
        if name in ('baseline', 'comment only'):
            assert process.returncode == 0, process.stderr
        else:
            assert process.returncode != 0 and 'FAIL:' in process.stderr, process.stderr
(root / 'evidence/mutations.json').write_text(json.dumps(report, indent=2) + '\n')
