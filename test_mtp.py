"""Test storage selection and staged replacement with a simulated KDE service."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mtp_io as m
from test_transfer import SLOT, kmz


class Storage:
    def __init__(self):
        self.path = f'{m.MISSION_ROOT}/{SLOT.folder}/{SLOT.folder}.kmz'
        self.files = {self.path: kmz(marker='old-test')}
        self.deleted = []

    def getFileMetadata(self, path, **kwargs):
        return (1 if path in self.files else 0, 0, SLOT.storage_id, '', len(self.files.get(path, b'')))

    def deleteObject(self, path, **kwargs):
        self.deleted.append(path)
        self.files.pop(path, None)
        return 0

    def setFileName(self, path, filename, **kwargs):
        self.files[str(Path(path).with_name(filename))] = self.files.pop(path)
        return 0


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / 'new.kmz'
        self.file.write_bytes(kmz(marker='new-test'))
        self.storage = Storage()
        self.original = self.storage.files[self.storage.path]
        self.corrupt = False
        self.fail = False

    def simulated_io(self, storage, operation, local, remote):
        if self.fail:
            raise m.TransferError('simulated staging failure')
        if operation == 'write':
            storage.files[remote] = b'corrupt-test' if self.corrupt else local.read_bytes()
        else:
            local.write_bytes(storage.files[remote])

    def run_copy(self):
        with patch('mtp_io.dbus.SessionBus'), patch('mtp_io.resolve', return_value=self.storage), \
             patch('mtp_io.storage_copy', side_effect=self.simulated_io):
            m.copy('write', self.file, SLOT)

    def test_valid_stage_then_replace(self):
        self.run_copy()
        self.assertEqual(self.storage.files, {self.storage.path: self.file.read_bytes()})
        self.assertEqual(self.storage.deleted, [self.storage.path])

    def test_staging_failure_leaves_original(self):
        self.fail = True
        with self.assertRaises(m.TransferError):
            self.run_copy()
        self.assertEqual(self.storage.files[self.storage.path], self.original)
        self.assertNotIn(self.storage.path, self.storage.deleted)

    def test_corrupt_stage_never_deletes_original(self):
        self.corrupt = True
        with self.assertRaisesRegex(m.TransferError, 'staged copy'):
            self.run_copy()
        self.assertEqual(self.storage.files, {self.storage.path: self.original})
        self.assertNotIn(self.storage.path, self.storage.deleted)


if __name__ == '__main__':
    unittest.main()
