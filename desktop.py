#!/usr/bin/env python3
"""One native planner window. Closing it releases the loopback port."""
import sys
from pathlib import Path
from PyQt6.QtCore import QLockFile, QUrl, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from server import start, DATA, ROOT


class Page(QWebEnginePage):
    def acceptNavigationRequest(self,url,kind,isMainFrame):
        return not isMainFrame or url.host()=='127.0.0.1' or url.scheme() in ('about','blob')


class Window(QMainWindow):
    def __init__(self,service):
        super().__init__(); self.service=service
        self.setWindowTitle('OpenDronePlanner'); self.setWindowIcon(QIcon(str(ROOT/'web/public/icon.svg'))); self.resize(1480,960)
        self.view=QWebEngineView(); self.profile=QWebEngineProfile('opendroneplanner',self)
        self.profile.setPersistentStoragePath(str(DATA/'browser')); self.profile.setCachePath(str(DATA/'cache'))
        self.page=Page(self.profile,self.view); self.view.setPage(self.page); self.setCentralWidget(self.view)
        self.page.printRequested.connect(self.print_page); self.profile.downloadRequested.connect(self.download); self.view.setUrl(QUrl(service.origin))
    def download(self,item):
        name,_=QFileDialog.getSaveFileName(self,'Save mission export',str(Path.home()/'Downloads'/item.downloadFileName()))
        if name:
            item.setDownloadDirectory(str(Path(name).parent)); item.setDownloadFileName(Path(name).name); item.accept()
        else: item.cancel()
    def print_page(self):
        self.printer=QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog=QPrintDialog(self.printer,self)
        if dialog.exec(): self.view.print(self.printer)
    def closeEvent(self,event):
        if self.service.usb_lock.locked():
            QMessageBox.information(self,'Controller operation in progress','Wait for the USB operation to finish before closing.'); event.ignore(); return
        self.service.stop_event.set(); self.service.shutdown(); self.service.server_close(); event.accept()


if __name__=='__main__':
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app=QApplication(sys.argv); app.setDesktopFileName('opendroneplanner')
    DATA.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(DATA/'desktop.lock'))
    if not lock.tryLock(100):
        QMessageBox.information(None,'OpenDronePlanner','OpenDronePlanner is already open. Select it on the taskbar.'); sys.exit(0)
    service=start(offline='--offline' in sys.argv); window=Window(service); window.show(); sys.exit(app.exec())
