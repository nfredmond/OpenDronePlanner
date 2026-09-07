"""Use system Qt on KDE; packaged desktop builds use LGPL PySide6."""
try:
    from PyQt6.QtCore import QLockFile, QUrl, Qt, QTimer
    from PyQt6.QtGui import QIcon, QDesktopServices
    from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QTabWidget
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
except ImportError:
    from PySide6.QtCore import QLockFile, QUrl, Qt, QTimer
    from PySide6.QtGui import QIcon, QDesktopServices
    from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QTabWidget
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PySide6.QtPrintSupport import QPrinter, QPrintDialog
