"""Validate KMZ files and replace a remembered DJI Fly slot through KDE MTP."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
try:
    import fcntl
except ImportError:
    fcntl=None
import io
import json
import math
import os
import re
import subprocess
import tempfile
import sys
import uuid
import xml.etree.ElementTree as ET
import zipfile

DATA = Path.home() / '.local/share/waypoint-transfer'
MISSION_ROOT = '/Android/data/dji.go.v5/files/waypoint'
UUID = re.compile(r'^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$')
MAX_FILE = 20 * 1024 * 1024


class TransferError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as output:
        json.dump(value, output, indent=2)
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


@dataclass(frozen=True)
class Mission:
    waypoints: int
    aircraft: str
    finish: str


def validate(data: bytes) -> Mission:
    if len(data) > MAX_FILE:
        raise TransferError('This KMZ exceeds the 20 MB transfer limit.')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [e.filename for e in entries]
            if len(entries) > 128 or len(set(names)) != len(names):
                raise ValueError('too many or duplicate archive entries')
            if sum(e.file_size for e in entries) > 64 * 1024 * 1024:
                raise ValueError('expanded archive too large')
            if any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in names):
                raise ValueError('unsafe archive path')
            documents = {}
            for name in ('wpmz/template.kml', 'wpmz/waylines.wpml'):
                text = archive.read(name).decode('utf-8-sig')
                if '\x00' in text or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
                    raise ValueError('XML declarations are not supported')
                documents[name] = ET.fromstring(text)
            route = documents['wpmz/waylines.wpml']
            points = route.findall('.//{*}Placemark')
            if not points:
                raise ValueError('no executable waypoints')
            for point in points:
                coords = point.findtext('.//{*}coordinates', '')
                values = [float(v) for v in coords.strip().split(',')]
                if len(values) < 2 or not all(math.isfinite(v) for v in values):
                    raise ValueError('invalid waypoint coordinates')
                if not -180 <= values[0] <= 180 or not -90 <= values[1] <= 90:
                    raise ValueError('coordinates out of range')
            aircraft = route.findtext('.//{*}droneEnumValue')
            if not aircraft:
                raise ValueError('missing aircraft identifier')
            return Mission(len(points), aircraft, route.findtext('.//{*}finishAction', 'unspecified'))
    except (zipfile.BadZipFile, KeyError, ValueError, ET.ParseError, RuntimeError, OSError) as error:
        raise TransferError(f'Not a usable DJI waypoint KMZ: {error}') from error


@dataclass(frozen=True)
class Slot:
    device: str
    serial: str
    storage: str
    folder: str
    storage_id: int


class KdeMtp:
    """Use KDE's existing MTP session, shared with Dolphin, without USB resets."""

    def discover(self) -> list[Slot]:
        if sys.platform!='linux':raise TransferError('Direct USB transfer currently requires Linux/KDE. Export the KMZ for your controller file manager.')
        if getattr(sys,'frozen',False):
            helper=Path(__file__).with_name('controller_discover.py')
            result=subprocess.run(['/usr/bin/python3',str(helper)],capture_output=True,text=True,timeout=90)
            if result.returncode:raise TransferError('KDE USB support requires python3-dbus, python3-gi and kio-extras. '+result.stderr[-700:])
            return [Slot(**s) for s in json.loads(result.stdout)]
        import dbus
        # Listing mtp:/ activates KDE's daemon when no file manager is open.
        subprocess.run(['kioclient', '--noninteractive', 'ls', 'mtp:/'],
                       capture_output=True, check=True, timeout=30)
        bus = dbus.SessionBus()
        service = 'org.kde.kmtpd5'
        daemon = dbus.Interface(bus.get_object(service, '/modules/kmtpd'), 'org.kde.kmtp.Daemon')
        slots = []
        seen = set()
        for device_path in daemon.listDevices(timeout=20):
            device = bus.get_object(service, device_path)
            props = dbus.Interface(device, 'org.freedesktop.DBus.Properties')
            name = str(props.Get('org.kde.kmtp.Device', 'friendlyName'))
            if not name.upper().startswith('DJI'):
                continue
            udi = str(props.Get('org.kde.kmtp.Device', 'udi'))
            sys_path = Path('/sys') / udi.split('/sys/', 1)[-1]
            serial_path = sys_path / 'serial'
            if not serial_path.is_file():
                raise TransferError('Cannot establish the controller identity. Reconnect it and try again.')
            serial = serial_path.read_text().strip()
            for storage_path in dbus.Interface(device, 'org.kde.kmtp.Device').listStorages():
                storage_obj = bus.get_object(service, storage_path)
                storage_name = str(dbus.Interface(storage_obj, 'org.freedesktop.DBus.Properties').Get(
                    'org.kde.kmtp.Storage', 'description'))
                storage = dbus.Interface(storage_obj, 'org.kde.kmtp.Storage')
                folders, error = storage.getFilesAndFolders(MISSION_ROOT, timeout=20)
                if error:
                    continue
                for folder in folders:
                    folder_name = str(folder[3])
                    if not UUID.fullmatch(folder_name) or str(folder[6]) != 'inode/directory':
                        continue
                    files, error = storage.getFilesAndFolders(f'{MISSION_ROOT}/{folder_name}', timeout=20)
                    if error:
                        continue
                    for item in files:
                        if str(item[3]) != folder_name + '.kmz' or not 0 < int(item[4]) <= MAX_FILE:
                            continue
                        # KDE can expose the same physical storage twice. Its MTP ID
                        # and file ID identify that alias without guessing by its name.
                        key = (serial, int(item[2]), int(item[0]))
                        if key not in seen:
                            seen.add(key)
                            slots.append(Slot(name, serial, storage_name, folder_name, int(item[2])))
        if len({s.serial for s in slots}) > 1:
            raise TransferError('More than one DJI controller is connected. Connect only the one to update.')
        return sorted(slots, key=lambda s: (s.storage_id, s.folder))

    def read(self, slot: Slot) -> bytes:
        with tempfile.TemporaryDirectory(prefix='waypoint-read-') as temporary:
            target = Path(temporary) / 'mission.kmz'
            self._io('read', slot, target)
            if target.stat().st_size > MAX_FILE:
                raise TransferError('Controller file exceeds the transfer limit.')
            return target.read_bytes()

    def write(self, slot: Slot, source: Path) -> None:
        self._io('write', slot, source)

    @staticmethod
    def _io(operation: str, slot: Slot, local: Path) -> None:
        helper = Path(__file__).with_name('mtp_io.py')
        result = subprocess.run(['/usr/bin/python3', str(helper), operation, str(local)],
                                input=json.dumps(asdict(slot)), capture_output=True,
                                text=True, timeout=90)
        if result.returncode:
            raise TransferError('USB copy failed. ' + result.stderr.strip()[-700:])


def transfer(source: Path, backend: KdeMtp, data_dir: Path = DATA) -> dict:
    """Back up, replace exactly one slot, read it back, and recover on failure."""
    if fcntl is None: raise TransferError('Direct controller transfer currently requires Linux/KDE. Export KMZ and copy it using the controller file manager.')
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (data_dir / 'transfer.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise TransferError('Another transfer is already running. Wait for it to finish.') from error
        return _transfer(source, backend, data_dir)


def _transfer(source: Path, backend: KdeMtp, data_dir: Path) -> dict:
    for receipt_path in (data_dir / 'backups').glob('*/receipt.json'):
        receipt = json.loads(receipt_path.read_text())
        if receipt.get('status') in ('writing', 'recovery_needed'):
            raise TransferError('A previous transfer needs recovery. Use Restore original before sending another flight.')
    if source.suffix.lower() != '.kmz' or not source.is_file():
        raise TransferError('Drop one local .kmz file.')
    if source.stat().st_size > MAX_FILE:
        raise TransferError('This KMZ exceeds the 20 MB transfer limit.')
    incoming = source.read_bytes()
    mission = validate(incoming)
    slots = backend.discover()
    if not slots:
        raise TransferError('No saved DJI flight was found. Connect and unlock the controller. '
                            'If needed, save a placeholder waypoint flight in DJI Fly first.')
    settings = data_dir / 'settings.json'
    remembered = json.loads(settings.read_text()) if settings.exists() else {}
    slot = next((s for s in slots if s.serial == remembered.get('serial')
                 and s.folder == remembered.get('folder') and s.storage_id == remembered.get('storage_id')), None)
    if slot is None:
        if remembered:
            raise TransferError('The remembered flight slot is missing or this is a different controller. '
                                'Use Reset slot choice before transferring.')
        slot = slots[0]
    original = backend.read(slot)
    previous = validate(original)
    if previous.aircraft != mission.aircraft:
        raise TransferError('The KMZ aircraft identifier differs from the saved flight. '
                            'Export a plan for the same aircraft before transferring.')
    if original == incoming:
        save_json(settings, asdict(slot))
        return {'status': 'unchanged', 'source': source.name, 'waypoints': mission.waypoints,
                'slot': asdict(slot), 'sha256': digest(incoming)}
    backup = data_dir / 'backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                                     + '-' + uuid.uuid4().hex[:8])
    backup.mkdir(parents=True, mode=0o700)
    for name, content in [('original.kmz', original), ('incoming.kmz', incoming)]:
        with (backup / name).open('xb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
    if (backup / 'original.kmz').read_bytes() != original:
        raise TransferError('The local backup could not be verified. Nothing was replaced.')
    receipt = {'status': 'backup_ready', 'slot': asdict(slot), 'source': str(source),
               'original_sha256': digest(original), 'sha256': digest(incoming),
               'waypoints': mission.waypoints, 'finish': mission.finish,
               'backup': str(backup)}
    save_json(backup / 'receipt.json', receipt)
    # Recheck after backup in case DJI Fly changed its file during preparation.
    if backend.read(slot) != original:
        raise TransferError('DJI Fly changed the saved flight during preparation. Nothing was replaced. Try again.')
    receipt['status'] = 'writing'
    save_json(backup / 'receipt.json', receipt)
    try:
        backend.write(slot, backup / 'incoming.kmz')
        actual = backend.read(slot)
        if actual != incoming:
            raise TransferError('The file read from the controller did not match the dropped KMZ.')
    except Exception as error:
        receipt['error'] = str(error)
        try:
            try:
                original_intact = backend.read(slot) == original
            except Exception:
                original_intact = False
            if not original_intact:
                backend.write(slot, backup / 'original.kmz')
                if backend.read(slot) != original:
                    raise TransferError('Restored file did not match its backup.')
            receipt['status'] = 'restored_after_failure'
        except Exception as restore_error:
            receipt['status'] = 'recovery_needed'
            receipt['restore_error'] = str(restore_error)
        save_json(backup / 'receipt.json', receipt)
        if receipt['status'] == 'recovery_needed':
            raise TransferError(f'Transfer failed and the original could not be restored. '
                                f'Do not use this flight slot. Reconnect and restore original.kmz from {backup}') from error
        raise TransferError(f'Transfer failed. The original flight is intact and verified. Backup: {backup}') from error
    receipt['status'] = 'verified'
    save_json(backup / 'receipt.json', receipt)
    save_json(settings, asdict(slot))
    return receipt


def restore_original(backend: KdeMtp, data_dir: Path = DATA) -> dict:
    """Restore the last backup, preferring an unfinished transaction, to its exact slot."""
    receipts = sorted((data_dir / 'backups').glob('*/receipt.json'), reverse=True)
    if not receipts:
        raise TransferError('There is no flight backup to restore yet.')
    pending = [p for p in receipts if json.loads(p.read_text()).get('status') in ('writing', 'recovery_needed')]
    path = (pending or receipts)[0]
    receipt = json.loads(path.read_text())
    original = path.parent / 'original.kmz'
    expected = original.read_bytes()
    validate(expected)
    if digest(expected) != receipt['original_sha256']:
        raise TransferError('The backup checksum does not match. Nothing was restored.')
    slot = Slot(**receipt['slot'])
    with (data_dir / 'transfer.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise TransferError('Another transfer is already running.') from error
        receipt['status'] = 'recovery_needed'
        save_json(path, receipt)
        backend.write(slot, original)
        if backend.read(slot) != expected:
            raise TransferError('The restored file did not match its backup. Keep this flight slot unused.')
        receipt['status'] = 'restored_by_user'
        save_json(path, receipt)
        return receipt
