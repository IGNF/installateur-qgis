from PyQt5.QtCore import Qt
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QProgressDialog

class DownloadProgress:
    def __init__(self, parent, total=0):
        self.progress = QProgressDialog("Téléchargement en cours...", "Annuler", 0, total, parent)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setWindowFlags(self.progress.windowFlags() | Qt.WindowStaysOnTopHint)
        self.progress.setMinimumDuration(0)  # Affiche immédiatement
        self.progress.setValue(0)
        self.progress.show()
        QCoreApplication.processEvents()

    def set_total(self, total):
        self.progress.setMaximum(total)
        self.progress.repaint()
        QCoreApplication.processEvents()

    def update(self, current, label=""):
        """Met à jour la barre avec l’index courant et le nom du plugin"""
        self.progress.setValue(current)
        if label:
            self.progress.setLabelText(f"{label} ({current}/{self.progress.maximum()})")
        self.progress.repaint()
        QCoreApplication.processEvents()

    def close(self):
        self.progress.close()
        QCoreApplication.processEvents()

# class DownloadProgress:
#     def __init__(self,parent):
#         self.progress = QProgressDialog("Téléchargement en cours", "Annuler", 0, 0,parent)
#         self.progress.setWindowModality(Qt.WindowModal)
#         self.progress.setWindowFlags(self.progress.windowFlags() | Qt.WindowStaysOnTopHint)
#         self.progress.show()
#         QCoreApplication.processEvents()
#
#     def setmaximum(self, maximum):
#         self.progress.setMaximum(maximum)
#         QCoreApplication.processEvents()
#
#     def setlabel(self,label):
#         self.progress.setLabelText(label)
#         QCoreApplication.processEvents()
#
#     def update(self, value):
#         # if maximum is not None:
#         #     self.progress.setMaximum(maximum)
#         self.progress.setValue(value)
#         QCoreApplication.processEvents()
#
#     def close(self):
#         self.progress.close()
#         QCoreApplication.processEvents()
