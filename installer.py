import os
import shutil
import stat
import sys
from datetime import datetime

from pypac import PACSession
import tldextract
from pathlib import Path

import requests
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtGui import QFont, QBrush, QColor
from PyQt5.QtWidgets import QApplication, QDialog, QTableWidgetItem, QMessageBox, QTableWidget,QInputDialog
from PyQt5.uic import loadUi

import tempfile
import zipfile
import xml.etree.ElementTree as ET

from progressbar import DownloadProgress

# PLUGINS_XML_GITHUB = "https://raw.githubusercontent.com/IGNF/collaboratif-plugins/main/plugins.xml?nocache=1"
# PLUGINS_XML_GITHUB = "https://raw.githubusercontent.com/IGNF/collaboratif-plugins/main/plugins_SDIS.xml?nocache=1"
PLUGINS_XML_GITHUB = "https://raw.githubusercontent.com/IGNF/collaboratif-plugins/main/plugins_collectivites.xml?nocache=1"



PAC_URL = "http://calamarlog.ign.fr/proxy.pac"
PLUGIN_MAITRE = "plugin_maitre"
FIC_LOG = "log.txt"
DOSSIER_A_GARDER = "config_plugin_maitre"
METADATA_FILE = "metadata.txt"
COLOR_MAJ = "#d4d400"
COLOR_NON_INSTALLE = "#ff6e6e"

TITRE = "Installateur de plugin IGN "
VERSION = "v0.3"


def log(message):
    """
    Écrit un message dans le fichier de log avec un horodatage.
    Le fichier est ouvert en mode append pour ne pas écraser les données.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(FIC_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


class InstallerDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.dossier_profil = None
        self.dico_plugin = {}
        # Charger le fichier .ui dans cette instance
        loadUi(self.resource_path("installer.ui"), self)

        self.pushButton_installer.clicked.connect(self.on_installe_plugin)
        self.pushButton_tout_rien.clicked.connect(self.on_tout_rien)
        self.pushButtonApropos.clicked.connect(self.on_a_propos)

    def on_a_propos(self):
        dlgAProposDe = QDialog()
        loadUi(os.path.dirname(__file__) + "/aproposde.ui", dlgAProposDe)
        dlgAProposDe.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        dlgAProposDe.setWindowTitle(f"{TITRE} {VERSION}")
        dlgAProposDe.pushButtonAffichedoc.clicked.connect(self.afficheDoc)
        dlgAProposDe.exec_()

    def afficheDoc(self):
        if not os.path.isfile(os.path.join(os.path.dirname(__file__), "installateur.pdf")):
            QMessageBox.warning(self,"Information","La documentation est introuvable")
        else:
            os.popen(os.path.join(os.path.dirname(__file__), "installateur.pdf"))

    def initialiser_apres_profil(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
            tmp_xml = tmp.name

        progress = DownloadProgress(self, 1)
        progress.update(1, "Connexion au dépot ...")
        if not self.download_file(PLUGINS_XML_GITHUB, tmp_xml):
            log("Impossible de télécharger plugins.xml")
            raise Exception("Impossible de télécharger plugins.xml")
        progress.close()

        self.getplugin_from_xml(tmp_xml)
        self.inti_dialog()

    def resource_path(self,relative_path):
        """Permet de trouver le chemin correct du fichier .ui, que ce soit en Python ou en exe PyInstaller"""
        try:
            # PyInstaller crée un dossier temporaire _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def inti_dialog(self):
        self.label_non_installe.setStyleSheet(f"background-color: {COLOR_MAJ}")
        self.pushButton_tout_rien.setStyleSheet("font : bold ")
        self.pushButton_installer.setStyleSheet("font : bold ;background-color: #00a108; color: white;")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        # tablewidget
        self.tablePlugins.horizontalHeader().setStyleSheet(
            "QHeaderView::section { color: white; background-color: #00a108; font-weight: bold; }")
        self.tablePlugins.setSelectionMode(QTableWidget.NoSelection)
        self.tablePlugins.setColumnCount(4)
        self.tablePlugins.setHorizontalHeaderLabels(["Plugins disponibles", "Version disponible","Version installée", "Description"])
        self.tablePlugins.setColumnWidth(0, 220)
        self.tablePlugins.setColumnWidth(1, 130)
        self.tablePlugins.setColumnWidth(2, 120)
        self.tablePlugins.setColumnWidth(3, 400)
        self.tablePlugins.horizontalHeader().setStretchLastSection(True)
        self.tablePlugins.setRowCount(len(self.dico_plugin))

        self.tablePlugins.verticalHeader().setMinimumSectionSize(1)
        self.tablePlugins.verticalHeader().setDefaultSectionSize(20)

        for row, (nom,valeur) in enumerate(self.dico_plugin.items()):
            version, description,lien = valeur
            item_name = QTableWidgetItem(nom)
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            if nom == PLUGIN_MAITRE:
                item_name.setCheckState(Qt.Checked)
                item_name.setFlags(item_name.flags() & ~Qt.ItemIsUserCheckable)
            else:
                item_name.setCheckState(Qt.Unchecked)
            font = QFont()
            font.setBold(True)
            item_name.setFont(font)
            self.tablePlugins.setItem(row, 0, item_name)
            self.tablePlugins.setItem(row, 1, QTableWidgetItem(str(version)))
            self.tablePlugins.setItem(row, 2, QTableWidgetItem(description))

            item_version = QTableWidgetItem(version)
            item_version.setFont(font)
            item_version.setFlags(item_version.flags() & ~Qt.ItemIsEditable)
            self.tablePlugins.setItem(row, 1, QTableWidgetItem(item_version))

            version_installe = self.get_version_plugins(nom)
            if version_installe is None:
                version_installe_text = "Non installé"
                item_version_installe = QTableWidgetItem(version_installe_text)
                item_version_installe.setBackground(QBrush(QColor(COLOR_NON_INSTALLE)))
            elif version_installe != version:
                version_installe_text = version_installe
                item_version_installe = QTableWidgetItem(version_installe_text)
                item_version_installe.setBackground(QBrush(QColor(COLOR_MAJ)))
            else:
                version_installe_text = version_installe
                item_version_installe = QTableWidgetItem(version_installe_text)

            item_version_installe.setFont(font)
            item_version_installe.setFlags(item_version_installe.flags() & ~Qt.ItemIsEditable)
            self.tablePlugins.setItem(row, 2, QTableWidgetItem(item_version_installe))

            item_descr = QTableWidgetItem(description)
            item_descr.setFlags(item_descr.flags() & ~Qt.ItemIsEditable)
            self.tablePlugins.setItem(row, 3, QTableWidgetItem(item_descr))

    def get_rep_plugin_qgis(self):
        # récupère le dossier d'installation des plugins dans QGIS
        # dossier utilisateur
        home = Path.home()
        chemin = os.path.join(home, f"AppData/Roaming/QGIS/QGIS3/profiles/{self.dossier_profil}/python/plugins")

        # si le profil est different de "default" il se peut que le dossier "plugins" n'existe pas
        # alors, on le crée
        if not os.path.exists(chemin):
            os.makedirs(chemin)

        if sys.platform.startswith("win"):
            return os.path.join(home, f"AppData/Roaming/QGIS/QGIS3/profiles/{self.dossier_profil}/python/plugins")
        elif sys.platform.startswith("darwin"):
            return os.path.join(home, f"Library/Application Support/QGIS/QGIS3/profiles/{self.dossier_profil}/python/plugins")
        else:
            return os.path.join(home, f".local/share/QGIS/QGIS3/profiles/{self.dossier_profil}/python/plugins")

    # def get_proxy_handler(self):
    #     http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    #     https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    #     proxies = {}
    #
    #     # Si aucun proxy défini → ne rien renvoyer
    #     if not http_proxy and not https_proxy:
    #         return {}
    #     proxy_to_test = https_proxy or http_proxy
    #     host, port = proxy_to_test.replace("http://", "").split(":")
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     sock.settimeout(1)
    #     try:
    #         sock.connect((host, int(port)))
    #         sock.close()
    #         proxies["http"] = http_proxy or https_proxy
    #         proxies["https"] = https_proxy or http_proxy
    #         print("Proxy détecté et fonctionnel :", proxies)
    #         return proxies
    #     except:
    #         print("Pas de proxy détecté")
    #         return {}

    # téléchargement de : plugins.xml
    def download_file(self,url, dest,timeout = 10):
        """
            Télécharge un fichier avec progression et essaye successivement :
            1) Proxy système
            2) Proxy PAC
            3) Sans proxy
            """

        print("Téléchargement de :", url)
        print("Téléchargement vers :", dest)
        log(f"Téléchargement de :{url}")

        attempts = [
            ("proxy système (env)", "ENV"),
            ("proxy.pac", "PAC"),
            ("sans proxy", "DIRECT")
        ]
        compt = 1
        for mode, proxy_mode in attempts:
            try:
                print(f"→ Tentative avec : {mode}")

                if proxy_mode == "ENV":
                    r = requests.get(url, stream=True, timeout=timeout)

                elif proxy_mode == "PAC":
                    tldextract.extract = tldextract.TLDExtract(suffix_list_urls=None)
                    session = PACSession()
                    r = session.get(url, stream=True, timeout=timeout)

                elif proxy_mode == "DIRECT":
                    session = requests.Session()
                    session.trust_env = False  # ⚠ ignore complètement HTTP_PROXY
                    r = session.get(url, stream=True, timeout=timeout)

                r.raise_for_status()

                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            QCoreApplication.processEvents()

                print(f"Connexion réussie avec : {mode}")
                log(f"Connexion réussie avec : {mode}")
                return True

            except Exception as e:
                print(f"Échec avec {mode} : {e}")
                log(f"Tentative connexion {compt}/3 : Échec {mode}")
                compt += 1

        log(f"Impossible de télécharger {url} après toutes les tentatives.")
        QMessageBox.critical(None, "erreur", f"Impossible de télécharger {url} après toutes les tentatives.")
        os.startfile(FIC_LOG)
        raise Exception("Impossible de télécharger le fichier après toutes les tentatives.")


        # ************************************************
        print("Téléchargement de :", url)
        print("Téléchargement vers  :", dest)
        print("HOST :", requests.utils.urlparse(url).netloc)
        # self.progress.show()
        attempts = [
            ("proxy système (HTTPS_PROXY)", {}),
            ("proxy.pac", "PAC"),
            ("sans proxy", {"http": None, "https": None})
        ]
        for mode, proxies in attempts:
            try:
                print(f"→ Tentative de connexion vers le dépot github avec : {mode}...")
                if proxies == "PAC":
                    tldextract.extract = tldextract.TLDExtract(suffix_list_urls=None)
                    session = PACSession()
                    r = session.get(url, stream=True, timeout=timeout)
                else:
                    r = requests.get(url, stream=True, proxies=proxies, timeout=timeout)

                r.raise_for_status()

                with open(dest, "wb") as f:
                    # lecture par petits paquets de 8ko
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            QCoreApplication.processEvents()

                print(f"Connexion réussie avec : {mode} -> {proxies}")
                log(f"Connexion réussie avec : {mode} -> {proxies}")
                log(f"Téléchargement de : {dest} -> terminé\n")
                return True

            except Exception as e:
                log(f"Échec connexion {mode}")

        # log(f"Impossible de télécharger {url} après toutes les tentatives.")
        raise Exception("Impossible de télécharger le fichier (ou plugin) après toutes les tentatives.")
        # ************************************************


    def getplugin_from_xml(self,tmp_xml):
        tree = ET.parse(tmp_xml)
        root = tree.getroot()
        list_tmp = ""
        self.dico_plugin = {}
        # Parcourir les plugins
        for plugin in root.findall("pyqgis_plugin"):
            name = plugin.get("name")
            version = plugin.get("version")
            description = plugin.find("description")
            download_url = plugin.find("download_url").text
            self.dico_plugin[name] = [version, description.text,download_url]
            list_tmp += f"-{name}\n"
        return self.dico_plugin


    def remove_readonly(self,func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)  # Retire l'attribut lecture seule
        func(path)  # Réessaie l'opération

    def telecharge_plugins(self,list_plugins):
        rep_installe = self.get_rep_plugin_qgis()
        compt = 0
        progress = DownloadProgress(self, len(list_plugins))
        for idx, plugin in enumerate(list_plugins, start=1):
            progress.update(idx, f"Téléchargement de : {plugin}")

            download_url = self.dico_plugin[plugin][2]
            fic_source = download_url

            fic_dest = f"{rep_installe}/{plugin}.zip"
            rep_plugin = os.path.join(rep_installe, plugin)
            if os.path.exists(rep_plugin):
                try:
                    # à faire : ne pas supprimer le sous dossier : DOSSIER_A_GARDER pour le plugin maitre
                    if plugin == PLUGIN_MAITRE:
                        self.suppr_plugin_maitre(rep_plugin)
                    else:
                        # Supprimer le dossier du plugin s'il existe déjà
                        shutil.rmtree(rep_plugin, onerror=self.remove_readonly)
                except Exception as e:
                    print("erreur" , e )
            self.download_file(fic_source, fic_dest)
            # Déziper dans le dossier des plugins
            try:
                with zipfile.ZipFile(fic_dest, 'r') as zip_ref:
                    zip_ref.extractall(rep_installe)
            except zipfile.BadZipFile:
                log(f"zip corrompu : {fic_dest}")
                pass
            # Supprimer le fichier zip
            os.remove(fic_dest)
            compt += 1
        progress.close()

    # suppression du dossier PLUGIN_MAITRE
    # c'est spécifique, car on veut garder le sous dossier : DOSSIER_A_GARDER (config des plugins)
    def suppr_plugin_maitre(self,rep_plugin):
        for item in os.listdir(rep_plugin):
            item_path = os.path.join(rep_plugin, item)
            if item in DOSSIER_A_GARDER:
                continue
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, onerror=self.remove_readonly)
            else:
                os.remove(item_path)

    def on_installe_plugin(self):
        self.list_plugin_installe = []
        for row in range(self.tablePlugins.rowCount()):
            item = self.tablePlugins.item(row, 0)  # colonne Nom
            if item.checkState() == Qt.Checked:
                plugin_name = item.text()
                self.list_plugin_installe.append(plugin_name)

        self.telecharge_plugins(self.list_plugin_installe)

        text = ("Installation terminé\n\n - Veuillez redémarrer QGIS pour prendre\n"
                "en compte les nouveaux plugins\n"
                " - Exécuter le 'plugin maitre' pour configurer les plugins")
        QMessageBox.information(self, "Installateur de plugins", text)

        # Mettre à jour uniquement les versions installées et la couleur
        for row, (nom, valeur) in enumerate(self.dico_plugin.items()):
            version = valeur[0]
            version_installe = self.get_version_plugins(nom)
            item_version_installe = self.tablePlugins.item(row, 2)  # colonne "Version installée"
            if version_installe is None:
                version_installe_text = "Non installé"
                item_version_installe.setText(version_installe_text)
                item_version_installe.setBackground(QBrush(QColor(COLOR_NON_INSTALLE)))
            elif version_installe != version:
                item_version_installe.setText(version_installe)
                item_version_installe.setBackground(QBrush(QColor(COLOR_MAJ)))
            else:
                item_version_installe.setText(version_installe)
                item_version_installe.setBackground(QBrush(Qt.white))

    def get_version_plugins(self,plugin_name):
        rep_plugin_qgis = self.get_rep_plugin_qgis()
        fic_metadata = os.path.join(rep_plugin_qgis, plugin_name,METADATA_FILE)
        if os.path.exists(fic_metadata):
            with open(fic_metadata, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("version="):
                        return line.strip().split("=")[1]
        return None

    def on_tout_rien(self):
        for row in range(self.tablePlugins.rowCount()):
            item = self.tablePlugins.item(row, 0)  # colonne Nom
            if not self.tablePlugins.item(row, 0).text() == PLUGIN_MAITRE:
                if item.checkState() == Qt.Checked:
                    item.setCheckState(Qt.Unchecked)
                    self.pushButton_tout_rien.setText("Tout")
                else:
                    item.setCheckState(Qt.Checked)
                    self.pushButton_tout_rien.setText("Rien")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = InstallerDialog()
    dlg.setWindowTitle(f"{TITRE} {VERSION}")

    if os.path.exists(FIC_LOG):
        os.remove(FIC_LOG)
    log("Lancement de l'installateur")

    chemin_profils = Path.home() / "AppData"/"Roaming"/"QGIS"/"QGIS3"/"profiles"
    # Affichage dans QMessageBox : convertir en slash pour HTML
    chemin_profils_aff = chemin_profils.as_posix()
    if not os.path.exists(chemin_profils):
        QMessageBox.warning(None,"Avertissement",f"<b>Avertissement :</b><br>Le répertoire de QGIS :<br><br><code>{chemin_profils_aff}</code><br><br>n'existe pas.")
        log(f"Le répertoire de QGIS : {chemin_profils_aff} -> n'existe pas.")
        sys.exit(1)

    # recuperation des différents profils de QGIS pour trouver le bon dossier d'installation des plugins
    rep_profils = [d.name for d in chemin_profils.iterdir() if d.is_dir()]
    if len(rep_profils) == 0 :
        QMessageBox.information(None,"Installateur de plugins","Aucun profil QGIS n'a été trouvé")
        log("aucun profil QGIS n'a été trouvé")
        sys.exit(1)

    ok = True
    if len(rep_profils) == 1 and rep_profils[0] == "default":
        dlg.dossier_profil = "default"
    else:
        dlg.dossier_profil, ok = QInputDialog.getItem(dlg,"Choisir un profil QGIS","Sélectionnez votre profil QGIS :",rep_profils,0,False)
        log(f"Le profil QGIS sélectionné est : {dlg.dossier_profil}")
    if not ok:
        sys.exit(0)

    rep_installe = dlg.get_rep_plugin_qgis()
    if not rep_installe:
        QMessageBox.warning(None, "Installateur de plugins", "Impossible de trouver le dossier d'installation des plugins QGIS")

    dlg.initialiser_apres_profil()
    dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
    dlg.exec_()






