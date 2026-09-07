#!/usr/bin/env python3
"""Native KDE drag-and-drop transfer window. No web server or login startup."""

from pathlib import Path
import json
import sys

from PyQt6.QtCore import QLockFile, QObject, QThread, QTimer, QUrl, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel,
                            QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget)

from transfer import DATA, KdeMtp, restore_original, transfer


class Work(QObject):
    finished = pyqtSignal(object, str)

    def __init__(self, action):
        super().__init__()
        self.action = action

    def run(self):
        try:
            self.finished.emit(self.action(), '')
        except Exception as error:
            self.finished.emit(None, str(error))


class DropArea(QFrame):
    dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName('dropArea')
        layout = QVBoxLayout(self)
        heading = QLabel('Drop your KMZ here')
        heading.setObjectName('dropTitle')
        layout.addWidget(heading)
        layout.addWidget(QLabel('The saved controller flight will be backed up and replaced.'))
        choose = QPushButton('Choose a KMZ file…')
        choose.clicked.connect(self.choose)
        layout.addWidget(choose)

    def choose(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Choose a waypoint plan',
                                                str(Path.home() / 'Downloads'), 'DJI flight plans (*.kmz)')
        if filename:
            self.dropped.emit(filename)

    def dragEnterEvent(self, event: QDragEnterEvent):
        urls = event.mimeData().urls()
        if self.isEnabled() and len(urls) == 1 and urls[0].isLocalFile() and urls[0].toLocalFile().lower().endswith('.kmz'):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if self.isEnabled() and len(urls) == 1 and urls[0].isLocalFile():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            self.dropped.emit(urls[0].toLocalFile())


class Window(QMainWindow):
    def __init__(self, offline=False):
        super().__init__()
        self.setWindowTitle('Waypoint Transfer')
        self.resize(740, 590)
        self.busy = False
        self.offline = offline
        self.thread = None
        self.worker = None
        content = QWidget()
        self.setCentralWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(17)
        title = QLabel('Waypoint Transfer')
        title.setObjectName('title')
        layout.addWidget(title)
        subtitle = QLabel('WaypointMap → your DJI controller')
        subtitle.setObjectName('subtitle')
        layout.addWidget(subtitle)
        self.connection = QLabel('Looking for a connected DJI controller…')
        self.connection.setWordWrap(True)
        layout.addWidget(self.connection)
        self.drop = DropArea()
        self.drop.dropped.connect(self.send)
        layout.addWidget(self.drop)
        self.status = QLabel('Connect and unlock the controller, then drop one exported KMZ.\n'
                             'Transfers begin automatically. Keep the USB cable connected.')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setMinimumHeight(86)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.refresh = QPushButton('Refresh connection')
        self.refresh.clicked.connect(self.scan)
        row.addWidget(self.refresh)
        self.reset = QPushButton('Reset slot choice')
        self.reset.clicked.connect(self.forget_slot)
        row.addWidget(self.reset)
        backups = QPushButton('Open backups')
        backups.clicked.connect(self.open_backups)
        row.addWidget(backups)
        layout.addLayout(row)
        self.restore = QPushButton('Restore original flight from backup')
        self.restore.clicked.connect(self.restore_backup)
        layout.addWidget(self.restore)
        note = QLabel('Copies the flight plan unchanged. Reopen the saved flight in DJI Fly and\n'
                      'check the route, altitude, and end action before flying. The thumbnail may be old.')
        note.setWordWrap(True)
        note.setObjectName('note')
        layout.addWidget(note)
        layout.addStretch()
        self.timer = QTimer(self)
        self.timer.setInterval(7000)
        self.timer.timeout.connect(self.scan)
        self.timer.start()
        QTimer.singleShot(0, self.scan)

    def start_work(self, action, callback):
        if self.busy:
            return
        self.busy = True
        self.refresh.setEnabled(False)
        self.reset.setEnabled(False)
        self.restore.setEnabled(False)
        self.drop.setEnabled(False)
        self.thread = QThread()
        self.worker = Work(action)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        def finished():
            self.busy = False
            self.refresh.setEnabled(True)
            self.reset.setEnabled(True)
            self.restore.setEnabled(True)
            self.drop.setEnabled(True)
            callback(*self.result)

        self.worker.finished.connect(self.record_result)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(finished)
        self.thread.start()

    @pyqtSlot(object, str)
    def record_result(self, result, error):
        self.result = (result, error)

    def scan(self):
        if self.offline:
            self.connection.setText('Controller access paused for local interface checks.')
            return
        def done(slots, error):
            if error:
                self.connection.setText('Controller unavailable. Unlock it and select USB file transfer, then refresh.')
                self.connection.setToolTip(error)
            elif not slots:
                self.connection.setText('No saved DJI flight found. Connect the controller and save a placeholder flight in DJI Fly.')
            else:
                remembered = DATA / 'settings.json'
                folder = ''
                if remembered.exists():
                    try:
                        folder = json.loads(remembered.read_text()).get('folder', '')
                    except (ValueError, OSError):
                        pass
                selected = next((s for s in slots if s.folder == folder), slots[0])
                self.connection.setText(f'{selected.device} connected · {len(slots)} saved flight slot(s)\n'
                                        f'Replacement slot: {selected.folder}')
                self.connection.setToolTip('This slot is backed up before each replacement.')
        self.start_work(lambda: KdeMtp().discover(), done)

    def send(self, filename: str):
        if self.busy:
            return
        if self.offline:
            self.status.setText('Controller access is paused. No flight was changed.')
            return
        self.status.setText(f'Transferring {Path(filename).name}…\nBacking up, copying, and reading the file back. Keep USB connected.')
        self.status.setStyleSheet('')

        def done(result, error):
            if error:
                self.status.setStyleSheet('color: #fda4af;')
                self.status.setText(error)
                return
            self.status.setStyleSheet('color: #86efac;')
            if result['status'] == 'unchanged':
                self.status.setText(f'Already on the controller · {result["waypoints"]} waypoints\n'
                                    'The saved KMZ matches this file byte for byte.')
            else:
                self.status.setText(f'Transferred and verified · {result["waypoints"]} waypoints\n'
                                    f'{Path(filename).name}\nOriginal flight saved in Backups.')
            self.connection.setText(f'{result["slot"]["device"]} connected\n'
                                    f'Replaced slot: {result["slot"]["folder"]}')
        self.start_work(lambda: transfer(Path(filename), KdeMtp()), done)

    def forget_slot(self):
        answer = QMessageBox.question(self, 'Reset slot choice',
                                      'Forget the saved slot choice? The next drop will use the first available '
                                      'flight slot. Existing backups will be kept.')
        if answer == QMessageBox.StandardButton.Yes:
            (DATA / 'settings.json').unlink(missing_ok=True)
            self.scan()

    def open_backups(self):
        path = DATA / 'backups'
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def restore_backup(self):
        if self.offline:
            return
        answer = QMessageBox.question(self, 'Restore original flight',
            'Replace the last transferred flight with its original backup? '
            'This uses the same controller and storage slot. Keep USB connected.')
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.status.setText('Restoring the original flight and checking the copied file…')
        def done(result, error):
            self.status.setStyleSheet('color: #fda4af;' if error else 'color: #86efac;')
            self.status.setText(error or 'Original flight restored and verified. You can transfer another KMZ.')
        self.start_work(lambda: restore_original(KdeMtp()), done)

    def closeEvent(self, event):
        if self.busy:
            self.status.setText('Please wait for the current controller operation to finish before closing.')
            event.ignore()
        else:
            self.timer.stop()
            event.accept()


def main():
    application = QApplication(sys.argv)
    application.setApplicationName('Waypoint Transfer')
    application.setDesktopFileName('waypoint-transfer')
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = QLockFile(str(DATA / 'window.lock'))
    if not lock.tryLock(0):
        QMessageBox.information(None, 'Waypoint Transfer', 'Waypoint Transfer is already open.')
        return 0
    application.setStyleSheet('''
        QMainWindow, QWidget { background: #101b2b; color: #e7eef8; font-size: 14px; }
        QLabel#title { font-size: 30px; font-weight: 700; }
        QLabel#subtitle { color: #9cb7d7; font-size: 17px; }
        QFrame#dropArea { border: 2px dashed #4b87a3; border-radius: 14px; padding: 22px; background: #152b3d; }
        QFrame#dropArea QLabel { background: transparent; border: none; padding: 4px; }
        QLabel#dropTitle { font-size: 25px; font-weight: 600; }
        QPushButton { background: #254760; border: 1px solid #496780; border-radius: 7px; padding: 11px 14px; }
        QPushButton:hover { background: #315c78; }
        QPushButton:disabled { color: #8a99ab; background: #233044; }
        QLabel#note { color: #a4b5ca; font-size: 12px; }
    ''')
    window = Window(offline='--offline' in sys.argv)
    window.show()
    return application.exec()


if __name__ == '__main__':
    sys.exit(main())
