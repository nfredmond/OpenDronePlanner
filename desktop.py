#!/usr/bin/env python3
"""One native planner window. Closing it releases the loopback port."""
import sys
import json
from pathlib import Path
from qt_compat import QLockFile, QUrl, Qt, QTimer, QIcon, QDesktopServices, QApplication, QMainWindow, QFileDialog, QMessageBox, QTabWidget, QWebEngineView, QWebEnginePage, QWebEngineProfile, QPrinter, QPrintDialog
from server import start, DATA, ROOT


class Page(QWebEnginePage):
    allowed_ports=[]
    def javaScriptConsoleMessage(self,level,message,line,source):
        print(f'Web console {level.name}: {message} ({source}:{line})',flush=True)
    def createWindow(self,kind):
        return self.owner.new_web_view().page()

    def acceptNavigationRequest(self,url,kind,isMainFrame):
        if isMainFrame and url.scheme()=='https':QDesktopServices.openUrl(url);return False
        return not isMainFrame or url.scheme() in ('about','blob') or (url.host()=='127.0.0.1' and url.port() in self.allowed_ports)


class Window(QMainWindow):
    def __init__(self,service):
        super().__init__(); self.service=service;service.native=True
        self.setWindowTitle('OpenDronePlanner'); self.setWindowIcon(QIcon(str(ROOT/'web/public/icon.svg'))); self.resize(1480,960)
        self.view=QWebEngineView(); self.profile=QWebEngineProfile('opendroneplanner',self)
        self.profile.setPersistentStoragePath(str(DATA/'browser')); self.profile.setCachePath(str(DATA/'cache'))
        self.tabs=QTabWidget();self.tabs.addTab(self.view,'Plan · Fly · Process · Present');self.setCentralWidget(self.tabs)
        self.page=Page(self.profile,self.view);self.page.owner=self;self.page.allowed_ports=[service.server_port]; self.view.setPage(self.page)
        self.timer=QTimer(self);self.timer.timeout.connect(self.open_requested);self.timer.start(250)
        self.web_view=None
        self.page.printRequested.connect(self.print_page); self.profile.downloadRequested.connect(self.download); self.view.setUrl(QUrl(service.origin))
    def new_web_view(self):
        view=QWebEngineView();page=Page(self.profile,view);page.owner=self;page.allowed_ports=[self.service.server_port,self.service.processing.port];view.setPage(page)
        self.tabs.addTab(view,'WebODM · Maps, models & measurements');self.tabs.setCurrentWidget(view)
        page.printRequested.connect(self.print_page);return view
    def open_requested(self):
        url=self.service.processing.open_request
        if url:
            self.service.processing.open_request=None
            if self.web_view is None:self.web_view=self.new_web_view()
            self.web_view.page().allowed_ports=[self.service.server_port,self.service.processing.port]
            self.web_view.setUrl(QUrl(url));self.tabs.setCurrentWidget(self.web_view)
    def download(self,item):
        name,_=QFileDialog.getSaveFileName(self,'Save OpenDronePlanner export',str(Path.home()/'Downloads'/item.downloadFileName()))
        if name:
            item.setDownloadDirectory(str(Path(name).parent)); item.setDownloadFileName(Path(name).name); item.accept()
        else: item.cancel()
    def print_page(self):
        self.printer=QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog=QPrintDialog(self.printer,self)
        if dialog.exec(): self.tabs.currentWidget().print(self.printer)
    def closeEvent(self,event):
        if self.service.usb_lock.locked():
            QMessageBox.information(self,'Controller operation in progress','Wait for the USB operation to finish before closing.'); event.ignore(); return
        try:
            if self.service.processing.engine_lock.locked() or self.service.processing.active():
                QMessageBox.information(self,'Processing is active','Finish or cancel processing before closing. Your current upload or reconstruction is still running.');event.ignore();return
            if self.service.processing.ready:self.service.processing.stop()
        except Exception as error:
            QMessageBox.warning(self,'Processing could not stop',str(error));event.ignore();return
        self.service.stop_event.set(); self.service.shutdown(); self.service.server_close(); event.accept()


if __name__=='__main__':
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app=QApplication(sys.argv); app.setDesktopFileName('opendroneplanner')
    DATA.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(DATA/'desktop.lock'))
    if not lock.tryLock(100):
        QMessageBox.information(None,'OpenDronePlanner','OpenDronePlanner is already open. Select it on the taskbar.'); sys.exit(0)
    service=start(offline='--offline' in sys.argv); window=Window(service); window.show()
    if '--self-test' in sys.argv:
        output=Path(sys.argv[sys.argv.index('--self-test')+1]);done={'value':False}
        def finish(value):
            if done['value']:return
            done['value']=True
            passed=bool(value and value.get('plan') and value.get('process'))
            output.write_text(json.dumps({'passed':passed,'port':service.server_port,'root':str(ROOT),'platform':sys.platform,'ui':value},indent=2))
            if passed:window.grab().save(str(output.with_suffix('.png')))
            window.close();app.exit(0 if passed else 1)
        def loaded(ok):
            if not ok:finish({'error':'Page failed to load'});return
            def click():
                window.page.runJavaScript("Boolean(document.querySelector('#map') && document.querySelector('[data-workflow=process]'))",lambda present:check(present))
            QTimer.singleShot(1500,click)
        def check(present):
            window.page.runJavaScript("document.querySelector('[data-workflow=process]')?.click()")
            QTimer.singleShot(1500,lambda:window.page.runJavaScript("JSON.stringify({process:document.querySelector('#processing-workspace')?.textContent.includes('Capture library')})",lambda value:finish({'plan':present,**json.loads(value or '{}')})))
        window.page.loadFinished.connect(loaded);QTimer.singleShot(60000,lambda:finish({'error':'Launch timed out'}))
    sys.exit(app.exec())
