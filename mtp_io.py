"""One bounded copy through KDE's MTP daemon, using an exact storage identifier."""

from pathlib import Path
import json
import sys
import tempfile
import uuid

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from transfer import MAX_FILE, MISSION_ROOT, Slot, TransferError, UUID


def resolve(bus, slot: Slot):
    service = 'org.kde.kmtpd5'
    daemon = dbus.Interface(bus.get_object(service, '/modules/kmtpd'), 'org.kde.kmtp.Daemon')
    matches = []
    for device_path in daemon.listDevices(timeout=15):
        device = bus.get_object(service, device_path)
        props = dbus.Interface(device, 'org.freedesktop.DBus.Properties')
        udi = str(props.Get('org.kde.kmtp.Device', 'udi'))
        serial_file = Path('/sys') / udi.split('/sys/', 1)[-1] / 'serial'
        if not serial_file.is_file() or serial_file.read_text().strip() != slot.serial:
            continue
        for storage_path in dbus.Interface(device, 'org.kde.kmtp.Device').listStorages():
            storage_obj = bus.get_object(service, storage_path)
            storage = dbus.Interface(storage_obj, 'org.kde.kmtp.Storage')
            parent = storage.getFileMetadata(MISSION_ROOT, timeout=15)
            if int(parent[0]) and int(parent[2]) == slot.storage_id:
                matches.append(storage)
    if len(matches) != 1:
        raise TransferError('The controller or selected storage is disconnected or ambiguous. No copy was started.')
    return matches[0]


def copy(operation: str, local: Path, slot: Slot):
    if operation not in ('read', 'write') or not UUID.fullmatch(slot.folder):
        raise TransferError('Invalid copy request.')
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    storage = resolve(bus, slot)
    remote = f'{MISSION_ROOT}/{slot.folder}/{slot.folder}.kmz'
    metadata = storage.getFileMetadata(remote, timeout=15)
    if operation == 'read' and (not int(metadata[0]) or int(metadata[4]) > MAX_FILE):
        raise TransferError('The saved KMZ is missing or too large.')
    if operation == 'write' and (not local.is_file() or not 0 < local.stat().st_size <= MAX_FILE):
        raise TransferError('The local file is missing or too large.')
    if operation == 'read':
        storage_copy(storage, 'read', local, remote)
        return
    # Prove a full upload and download before removing the original flight.
    stage = f'{MISSION_ROOT}/{slot.folder}/transfer-{uuid.uuid4().hex}.kmz'
    staged = False
    try:
        storage_copy(storage, 'write', local, stage)
        staged = True
        with tempfile.TemporaryDirectory(prefix='waypoint-stage-') as directory:
            downloaded = Path(directory) / 'check.kmz'
            storage_copy(storage, 'read', downloaded, stage)
            if downloaded.read_bytes() != local.read_bytes():
                raise TransferError('The staged copy did not match. The original was not removed.')
        if int(metadata[0]) and storage.deleteObject(remote, timeout=15) != 0:
            raise TransferError('The old KMZ could not be replaced.')
        if storage.setFileName(stage, slot.folder + '.kmz', timeout=15) != 0:
            raise TransferError('The new KMZ could not be renamed. Recovery is required.')
        staged = False
    finally:
        if staged:
            # Only this operation's uniquely named temporary file is eligible.
            try:
                storage.deleteObject(stage, timeout=15)
            except Exception:
                pass


def storage_copy(storage, operation: str, local: Path, remote: str):
    loop = GLib.MainLoop()
    result = []

    def finished(code):
        result.append(int(code))
        loop.quit()

    def expired():
        result.append(-1)
        loop.quit()
        return False

    signal = storage.connect_to_signal('copyFinished', finished)
    timer = GLib.timeout_add_seconds(60, expired)
    try:
        with local.open('rb' if operation == 'write' else 'xb') as file:
            descriptor = dbus.types.UnixFd(file.fileno())
            if operation == 'write':
                code = storage.sendFileFromFileDescriptor(descriptor, remote, timeout=15)
            else:
                code = storage.getFileToFileDescriptor(descriptor, remote, timeout=15)
            if code:
                raise TransferError('KDE could not begin the file copy.')
            if not result:
                loop.run()
            if result != [0]:
                raise TransferError('The controller copy failed or timed out. Keep USB connected.')
    finally:
        signal.remove()
        if not result or result[0] != -1:
            GLib.source_remove(timer)


if __name__ == '__main__':
    try:
        copy(sys.argv[1], Path(sys.argv[2]), Slot(**json.load(sys.stdin)))
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
