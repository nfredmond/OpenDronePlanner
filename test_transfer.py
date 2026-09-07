"""Local tests with synthetic KMZ fixtures and a simulated device. No USB access."""

import fcntl
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import transfer as t


def kmz(aircraft='68', coordinate='-121,39', marker='test'):
    stream = io.BytesIO()
    xml = (f'<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>{marker}</name>'
           f'<droneEnumValue>{aircraft}</droneEnumValue><finishAction>noAction</finishAction>'
           '<Folder><Placemark><Point>'
           f'<coordinates>{coordinate}</coordinates></Point></Placemark></Folder></Document></kml>')
    with zipfile.ZipFile(stream, 'w') as z:
        z.writestr('wpmz/template.kml', '<kml/>')
        z.writestr('wpmz/waylines.wpml', xml)
    return stream.getvalue()


SLOT = t.Slot('DJI Test', 'TEST-SERIAL', 'Storage', '11111111-1111-1111-1111-111111111111', 65537)


class FakeDevice:
    def __init__(self):
        self.data = kmz(marker='original-test')
        self.slots = [SLOT]
        self.writes = []
        self.reads = 0
        self.corrupt_write = False
        self.fail_write = False
        self.disconnected = False
        self.conflict = False

    def discover(self):
        return self.slots

    def read(self, slot):
        self.reads += 1
        if self.disconnected and self.writes:
            raise OSError('simulated disconnect')
        if self.conflict and self.reads == 2:
            return kmz(marker='concurrent-test-edit')
        return self.data

    def write(self, slot, source):
        self.writes.append((slot, source))
        if self.disconnected or self.fail_write and len(self.writes) == 1:
            raise OSError('simulated USB failure')
        self.data = b'corrupt-test' if self.corrupt_write and len(self.writes) == 1 else source.read_bytes()


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'incoming.kmz'
        self.source.write_bytes(kmz(marker='incoming-test'))
        self.data = self.root / 'data'
        self.device = FakeDevice()

    def run_transfer(self):
        return t.transfer(self.source, self.device, self.data)

    def receipt(self):
        return json.loads(next((self.data / 'backups').glob('*/receipt.json')).read_text())

    def test_success_backs_up_and_reads_back_unchanged_bytes(self):
        original = self.device.data
        result = self.run_transfer()
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(self.device.data, self.source.read_bytes())
        self.assertGreaterEqual(self.device.reads, 3)
        self.assertEqual((Path(result['backup']) / 'original.kmz').read_bytes(), original)
        self.assertEqual(len(self.device.writes), 1)
        self.assertEqual(json.loads((self.data / 'settings.json').read_text())['storage_id'], 65537)

    def test_identical_source_does_not_write(self):
        self.source.write_bytes(self.device.data)
        self.assertEqual(self.run_transfer()['status'], 'unchanged')
        self.assertFalse(self.device.writes)

    def test_bad_zip_does_not_write(self):
        self.source.write_bytes(b'not a zip')
        with self.assertRaisesRegex(t.TransferError, 'KMZ'):
            self.run_transfer()
        self.assertFalse(self.device.writes)

    def test_wrong_aircraft_does_not_write(self):
        self.source.write_bytes(kmz(aircraft='OTHER'))
        with self.assertRaisesRegex(t.TransferError, 'aircraft'):
            self.run_transfer()
        self.assertFalse(self.device.writes)

    def test_missing_device_does_not_write(self):
        self.device.slots = []
        with self.assertRaisesRegex(t.TransferError, 'No saved'):
            self.run_transfer()
        self.assertFalse(self.device.writes)

    def test_remembered_missing_slot_never_falls_back(self):
        t.save_json(self.data / 'settings.json', {**t.asdict(SLOT), 'serial': 'DIFFERENT'})
        with self.assertRaisesRegex(t.TransferError, 'remembered'):
            self.run_transfer()
        self.assertFalse(self.device.writes)

    def test_same_names_different_storage_remembered_exactly(self):
        second = t.Slot(SLOT.device, SLOT.serial, SLOT.storage, SLOT.folder, 131073)
        self.device.slots.append(second)
        t.save_json(self.data / 'settings.json', t.asdict(second))
        self.run_transfer()
        self.assertEqual(self.device.writes[0][0].storage_id, 131073)

    def test_failed_backup_never_writes(self):
        with patch('transfer.os.fsync', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.run_transfer()
        self.assertFalse(self.device.writes)

    def test_controller_changed_after_backup_never_writes(self):
        self.device.conflict = True
        with self.assertRaisesRegex(t.TransferError, 'changed'):
            self.run_transfer()
        self.assertFalse(self.device.writes)

    def test_corrupt_copy_is_restored_and_never_success(self):
        original = self.device.data
        self.device.corrupt_write = True
        with self.assertRaisesRegex(t.TransferError, 'intact and verified'):
            self.run_transfer()
        self.assertEqual(self.device.data, original)
        self.assertEqual(self.receipt()['status'], 'restored_after_failure')

    def test_failed_copy_is_restored(self):
        original = self.device.data
        self.device.fail_write = True
        with self.assertRaisesRegex(t.TransferError, 'intact and verified'):
            self.run_transfer()
        self.assertEqual(self.device.data, original)

    def test_disconnect_keeps_original_and_recovery_record(self):
        original = self.device.data
        self.device.disconnected = True
        with self.assertRaisesRegex(t.TransferError, 'Do not use this flight slot'):
            self.run_transfer()
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 'recovery_needed')
        self.assertEqual((Path(receipt['backup']) / 'original.kmz').read_bytes(), original)

    def test_second_process_cannot_transfer(self):
        self.data.mkdir()
        with (self.data / 'transfer.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(t.TransferError, 'already running'):
                self.run_transfer()
        self.assertFalse(self.device.writes)

    def test_bad_coordinates_refused(self):
        for coords in ['nan,39', '181,39', '-121,91', 'not-a-coordinate']:
            with self.subTest(coords=coords), self.assertRaises(t.TransferError):
                t.validate(kmz(coordinate=coords))

    def test_missing_wpml_refused(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('doc.kml', '<kml/>')
        with self.assertRaises(t.TransferError):
            t.validate(stream.getvalue())

    def test_xml_entity_refused(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('wpmz/template.kml', '<!DOCTYPE kml [<!ENTITY x "test">]><kml/>')
            archive.writestr('wpmz/waylines.wpml', '<kml/>')
        with self.assertRaisesRegex(t.TransferError, 'XML declarations'):
            t.validate(stream.getvalue())

    def test_pending_recovery_blocks_new_transfer(self):
        t.save_json(self.data / 'backups/pending/receipt.json', {'status': 'writing'})
        with self.assertRaisesRegex(t.TransferError, 'recovery'):
            self.run_transfer()
        self.assertFalse(self.device.writes)

    def test_restore_original_uses_recorded_slot_and_bytes(self):
        original = self.device.data
        self.run_transfer()
        result = t.restore_original(self.device, self.data)
        self.assertEqual(result['status'], 'restored_by_user')
        self.assertEqual(self.device.data, original)
        self.assertEqual(self.device.writes[-1][0], SLOT)

    def test_changed_backup_cannot_be_restored(self):
        result = self.run_transfer()
        (Path(result['backup']) / 'original.kmz').write_bytes(kmz(marker='tampered-test'))
        before = len(self.device.writes)
        with self.assertRaisesRegex(t.TransferError, 'checksum'):
            t.restore_original(self.device, self.data)
        self.assertEqual(len(self.device.writes), before)


if __name__ == '__main__':
    unittest.main()
