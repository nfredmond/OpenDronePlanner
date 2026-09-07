"""Read-only discovery through the system Python/KDE bindings in bundled builds."""
import json
from dataclasses import asdict
from transfer import KdeMtp
if __name__=='__main__': print(json.dumps([asdict(slot) for slot in KdeMtp().discover()]))
