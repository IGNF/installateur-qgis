from PyQt6.QtCore import Qt,QCoreApplication
from PyQt6.QtWidgets import QProgressDialog

class DownloadProgress:
    def __init__(self, parent, total=0):
        self.progress = QProgressDialog("Téléchargement en cours...", "Annuler", 0, total, parent)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setWindowFlags(self.progress.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.progress.setMinimumDuration(0)  # Affiche immédiatement
        self.progress.setValue(0)
        self.progress.show()
        QCoreApplication.processEvents()

    def update(self, current, label=""):
        """Met à jour la barre avec l’index courant """
        self.progress.setValue(current)
        if label:
            self.progress.setLabelText(f"{label}")
        self.progress.repaint()
        QCoreApplication.processEvents()

    def getMaximum(self):
        return self.progress.maximum()

    def setlabel(self, label):
        self.progress.setLabelText(label)
        QCoreApplication.processEvents()

    def close(self):
        self.progress.close()
        QCoreApplication.processEvents()

