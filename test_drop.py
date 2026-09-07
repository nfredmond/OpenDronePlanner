"""Exercise native Qt drop events without contacting the controller."""

import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import unittest
from PyQt6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QApplication
from app import DropArea


class DropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication([])

    def test_drop_is_always_a_copy_and_emits_local_filename(self):
        area = DropArea()
        received = []
        area.dropped.connect(received.append)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile('/tmp/synthetic-test.kmz')])
        actions = Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
        enter = QDragEnterEvent(QPoint(2, 2), actions, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        enter.setDropAction(Qt.DropAction.MoveAction)
        area.dragEnterEvent(enter)
        self.assertTrue(enter.isAccepted())
        self.assertEqual(enter.dropAction(), Qt.DropAction.CopyAction)
        drop = QDropEvent(QPointF(2, 2), actions, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        drop.setDropAction(Qt.DropAction.MoveAction)
        area.dropEvent(drop)
        self.assertEqual(drop.dropAction(), Qt.DropAction.CopyAction)
        self.assertEqual(received, ['/tmp/synthetic-test.kmz'])

    def test_remote_and_multiple_files_are_rejected(self):
        area = DropArea()
        for urls in [[QUrl('https://example.com/test.kmz')],
                     [QUrl.fromLocalFile('/tmp/a.kmz'), QUrl.fromLocalFile('/tmp/b.kmz')]]:
            mime = QMimeData()
            mime.setUrls(urls)
            event = QDragEnterEvent(QPoint(2, 2), Qt.DropAction.CopyAction, mime,
                                    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            area.dragEnterEvent(event)
            self.assertFalse(event.isAccepted())


if __name__ == '__main__':
    unittest.main()
