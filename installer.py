import os
import shutil
import stat
import sys
import webbrowser
from datetime import datetime

from pypac import PACSession
import tldextract
from pathlib import Path

import requests
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QFont, QBrush, QColor
from PyQt6.QtWidgets import QApplication, QDialog, QTableWidgetItem, QMessageBox, QInputDialog, \
    QAbstractItemView, QComboBox
from PyQt6.uic import loadUi

import tempfile
import zipfile
import xml.etree.ElementTree as ET

from progressbar import DownloadProgress
from urllib.parse import urlparse


# ==== TOUS ====
PLUGINS_XML_GITHUB = "https://raw.githubusercontent.com/IGNF/collaboratif-plugins/main/plugins.xml?nocache=1"
# ==== SDIS ====
# PLUGINS_XML_GITHUB = "https://raw.githubusercontent.com/IGNF/collaboratif-plugins/main/plugins_sdis.xml?nocache=1"
# ==== COLLECTIVITES ====
# PLUGINS_XML_GITHUB = "https://raw.githubusercontent.com/IGNF/collaboratif-plugins/main/plugins_collectivites.xml?nocache=1"
# ==== TEST ====
# PLUGINS_XML_GITHUB = "https://raw.githubusercontent.com/IGNF/collaboratif-plugins/main/plugins_test.xml?nocache=1"
# ==== RECETTE ====
# PLUGINS_XML_GITHUB = "https://raw.githubusercontent.com/IGNF/collaboratif-plugins/main/plugins_recette.xml?nocache=1"


REP_QGIS = "AppData/Roaming/QGIS"

PAC_URL = "http://calamarlog.ign.fr/proxy.pac"
PLUGIN_MAITRE = "PluginsManager"
INSTALLATEUR = "PluginIGN_Installer"
FIC_LOG = "log_installateur.txt"
DOSSIER_A_GARDER = "config_PluginsManager"
METADATA_FILE = "metadata.txt"
COLOR_MAJ = "#FFF176"
COLOR_COMBO = "#bababa"
COLOR_NON_INSTALLE = "#ff6e6e"

TITRE = f"{INSTALLATEUR} : Installateur de plugins IGN"


def log(message,reset=False):
    """
    Écrit un message dans le fichier de log avec un horodatage.
    Le fichier est ouvert en mode append pour ne pas écraser les données.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode = "w" if reset else "a"  # "w" pour écraser, "a" pour ajouter
    with open(FIC_LOG, mode, encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


class InstallerDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.dossier_profil = None
        self.dico_plugin_from_xml = {}
        # aucun plugin n’est coché.
        self.ischeck = False

        # Charger le fichier .ui dans cette instance
        loadUi(self.resource_path("installer.ui"), self)

        self.pushButton_installer.clicked.connect(self.on_installe_plugin)
        self.pushButton_tout_rien.clicked.connect(self.on_tout_rien)
        self.pushButtonApropos.clicked.connect(self.on_a_propos)

    def on_a_propos(self):
        dlgAProposDe = QDialog()
        loadUi(os.path.dirname(__file__) + "/aproposde.ui", dlgAProposDe)
        dlgAProposDe.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowCloseButtonHint)
        dlgAProposDe.setWindowTitle(f"{TITRE}")
        dlgAProposDe.pushButtonAffichedoc.clicked.connect(self.afficheDoc)
        dlgAProposDe.exec()

    def afficheDoc(self):
        webbrowser.open("https://ignf.github.io/installateur-qgis/")

    def initialiser_apres_profil(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
            tmp_xml = tmp.name

        progress = DownloadProgress(self, 1)
        progress.update(1, "Connexion au dépot ...")
        if self.download_file(PLUGINS_XML_GITHUB, tmp_xml):
            self.getplugin_from_xml(tmp_xml)
            self.inti_dialog()
            return True
        else:
            progress.close()
            return False

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
        self.pushButton_tout_rien.setStyleSheet("font : bold ;background-color: #00b909; color: black;")
        self.pushButton_installer.setStyleSheet("font : bold ;background-color: #00b909; color: black;")
        self.pushButtonApropos.setStyleSheet("font : bold ;background-color: #00e70b; color: black;")

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowCloseButtonHint)
        # tablewidget
        self.tablePlugins.horizontalHeader().setStyleSheet(
            "QHeaderView::section { color: white; background-color: #00a108; font-weight: bold; }")
        self.tablePlugins.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tablePlugins.setColumnCount(5)
        self.tablePlugins.setHorizontalHeaderLabels(["Plugins disponibles", "Version disponible","Version installée", "Description","Dernières modifications"])
        self.tablePlugins.setColumnWidth(0, 220)
        self.tablePlugins.setColumnWidth(1, 130)
        self.tablePlugins.setColumnWidth(2, 120)
        self.tablePlugins.setColumnWidth(3, 350)
        self.tablePlugins.setColumnWidth(4, 400)
        self.tablePlugins.horizontalHeader().setStretchLastSection(True)

        self.tablePlugins.verticalHeader().setMinimumSectionSize(1)
        self.tablePlugins.verticalHeader().setDefaultSectionSize(20)

        # tablewidget info
        self.init_tablewidget_info()

        for nom,valeur in self.dico_plugin_from_xml.items():
            # si c'est l'installateur, on ne l'ajoute pas dans la liste,
            # on l'installe par défaut
            if INSTALLATEUR in nom:
                continue
            version = valeur["version"]
            description = valeur["description"]
            changelog = valeur["changelog"]
            version_installe = self.get_version_plugins(nom)

            ligne = self.tablePlugins.rowCount()
            self.tablePlugins.insertRow(ligne)

            item_name = QTableWidgetItem(nom)
            item_version_dispo = QTableWidgetItem(version)
            item_version_installe = QTableWidgetItem(version_installe)
            item_descr = QTableWidgetItem(description)
            # combobox pour le changelog sinon QTableWidgetItem
            item_changelog = QTableWidgetItem(changelog)
            item_changelog_combo = QComboBox()

            # TODO : verifier si connexion internet !!

            # si changelog est une liste
            if not changelog:
                changelog = "Aucune information sur les dernières modifications"
                item_changelog.setText(changelog)
            changelog  = changelog.replace("\\n", "\n")
            list_log = changelog.splitlines()
            item_changelog_combo.addItems(list_log)
            # si changelog est sur plusieurs lignes, on colorie la cellule
            if len(list_log) > 1:
                item_changelog_combo.setStyleSheet(f"background-color: {COLOR_COMBO}")

            if nom == PLUGIN_MAITRE:
                item_name.setCheckState(Qt.CheckState.Checked)
                item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            else:
                item_name.setCheckState(Qt.CheckState.Unchecked)

            if version_installe is None:
                item_version_installe.setText("Non installé")
                item_name.setCheckState(Qt.CheckState.Checked)
                item_version_installe.setBackground(QBrush(QColor(COLOR_NON_INSTALLE)))
            elif version_installe != version:
                item_name.setCheckState(Qt.CheckState.Checked)
                item_version_dispo.setBackground(QBrush(QColor(COLOR_MAJ)))
            else:
                item_version_installe.setText(version_installe)

            font = QFont()
            font.setBold(True)

            item_name.setFont(font)
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tablePlugins.setItem(ligne, 0, item_name)

            item_version_dispo.setFont(font)
            item_version_dispo.setFlags(item_version_dispo.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tablePlugins.setItem(ligne, 1, item_version_dispo)

            item_version_installe.setFont(font)
            item_version_installe.setFlags(item_version_installe.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tablePlugins.setItem(ligne, 2, item_version_installe)

            item_descr.setFlags(item_descr.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tablePlugins.setItem(ligne, 3, item_descr)

            if len(list_log) >1:
                self.tablePlugins.setCellWidget(ligne, 4, item_changelog_combo)
            else:
                self.tablePlugins.setItem(ligne, 4, item_changelog)


    def init_tablewidget_info(self):
        self.tableWidget_info.setColumnCount(2)
        self.tableWidget_info.horizontalHeader().setVisible(False)
        self.tableWidget_info.verticalHeader().setVisible(False)
        self.tableWidget_info.setShowGrid(False)

        file_xml = os.path.basename(urlparse(PLUGINS_XML_GITHUB).path)

        self.tableWidget_info.setRowCount(3)

        donnees = [
            ("version de QGIS", f": {self.dossier_qgis}"),
            ("profil utilisateur", f": {self.dossier_profil}"),
            ("xml des plugins", f": {file_xml}")
        ]
        font = QFont()
        font.setBold(True)
        for ligne , (propriete, valeur) in enumerate(donnees):
            item_propriete = QTableWidgetItem(propriete)
            item_propriete.setFlags(item_propriete.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_propriete.setFont(font)
            self.tableWidget_info.setItem(ligne, 0, item_propriete)
            item_valeur = QTableWidgetItem(valeur)
            item_valeur.setFlags(item_valeur.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # item_valeur.setFont(font)
            self.tableWidget_info.setItem(ligne, 1, item_valeur)

        self.tableWidget_info.resizeColumnsToContents()
        self.tableWidget_info.resizeRowsToContents()

    def get_rep_plugin_qgis(self):
        # récupère le dossier d'installation des plugins dans QGIS
        # dossier utilisateur
        home = Path.home()

        chemin = os.path.join(home, f"AppData/Roaming/QGIS/{self.dossier_qgis}/profiles/{self.dossier_profil}/python/plugins")

        # si le profil est different de "default" il se peut que le dossier "plugins" n'existe pas
        # alors, on le crée
        if not os.path.exists(chemin):
            os.makedirs(chemin)

        if sys.platform.startswith("win"):
            return os.path.join(home, f"AppData/Roaming/QGIS/{self.dossier_qgis}/profiles/{self.dossier_profil}/python/plugins")
        elif sys.platform.startswith("darwin"):
            return os.path.join(home, f"Library/Application Support/QGIS/{self.dossier_qgis}/profiles/{self.dossier_profil}/python/plugins")
        else:
            return os.path.join(home, f".local/share/QGIS/{self.dossier_qgis}/profiles/{self.dossier_profil}/python/plugins")


    # téléchargement de : plugins.xml
    def download_file(self,url, dest,timeout = 10):
        """
            Télécharge un fichier avec progression et essaye successivement :
            1) Proxy système
            2) Proxy PAC
            3) Sans proxy
            """

        log(f"Téléchargement de :{url} vers {dest}")

        attempts = [
            ("proxy système (env)", "ENV"),
            ("proxy.pac", "PAC"),
            ("sans proxy", "DIRECT")
        ]
        compt = 1
        for mode, proxy_mode in attempts:
            try:
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

                log(f"Connexion réussie avec : {mode}")
                return True

            except Exception as e:
                log(f"Tentative connexion {compt}/3 : Échec {mode}")
                compt += 1

        log(f"Impossible de télécharger {url} après toutes les tentatives.")
        text_erreur = (f"Impossible de télécharger le fichier nécessaire à l'installation des plugins :\n\n"
                f"{url}\n\n"
                "Veuillez vérifier votre connexion internet et vos paramètres de proxy.\n"
                "Le fichier de log va s'ouvrir pour plus de détails.")
        QMessageBox.critical(self, "Erreur critique", text_erreur)
        os.startfile(FIC_LOG)
        return False

    def getplugin_from_xml(self,tmp_xml):
        tree = ET.parse(tmp_xml)
        root = tree.getroot()
        self.dico_plugin_from_xml = {}
        # Parcourir les plugins
        for plugin in root.findall("pyqgis_plugin"):
            name = plugin.get("name")
            version = plugin.get("version")
            description = plugin.find("description")
            changelog = plugin.find("changelog")
            log(f"Plugin trouvé dans le xml : {name} version {version}")
            if changelog is None:
                changelog = ET.Element("changelog")
                changelog.text = ""
            download_url = plugin.find("download_url").text
            # self.dico_plugin_from_xml[name] = [version, description.text, changelog.text, download_url]
            # plus explicite
            self.dico_plugin_from_xml[name] = {
                "version": version,
                "description": description.text,
                "changelog": changelog.text,
                "download_url": download_url
            }
        return self.dico_plugin_from_xml


    def remove_readonly(self,func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)  # Retire l'attribut lecture seule
        func(path)  # Réessaie l'opération

    def telecharge_plugins(self,list_plugins):
        rep_installe = self.get_rep_plugin_qgis()
        compt = 0
        progress = DownloadProgress(self, len(list_plugins)+1)
        for idx, plugin in enumerate(list_plugins, start=1):
            log(f"Téléchargement de : {plugin} version : {self.dico_plugin_from_xml[plugin]['version']}")
            progress.update(idx, f"Téléchargement de : {plugin}")
            download_url = self.dico_plugin_from_xml[plugin]['download_url']
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
                    log(f"dezip de : {fic_dest}")
            except zipfile.BadZipFile:
                log(f"ZIP corrompu : {fic_dest}")
            except FileNotFoundError:
                log(f"Fichier introuvable : {fic_dest}")
            except PermissionError:
                log(f"Permission refusée : {fic_dest}")
            except Exception as e:
                log(f"Erreur dézip : {e}")

            # Supprimer le fichier zip
            log(f"Suppression du fichier zip : {fic_dest}")
            os.remove(fic_dest)
            compt += 1
        return progress

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
            if item.checkState() == Qt.CheckState.Checked:
                plugin_name = item.text()
                self.list_plugin_installe.append(plugin_name)
        # on ajoute l'installateur dans la liste des plugins à installer,
        # car il n'est pas dans la liste
        for plugin in self.dico_plugin_from_xml:
            if INSTALLATEUR in plugin:
                self.list_plugin_installe.append(plugin)
        progress = self.telecharge_plugins(self.list_plugin_installe)
        progress.setlabel("Finalisation de l'installation")

        # Mettre à jour uniquement les versions installées et la couleur
        for row in range(self.tablePlugins.rowCount()):
            nom = self.tablePlugins.item(row, 0).text()
            valeur = self.dico_plugin_from_xml.get(nom)
            if not valeur:
                continue
            version = valeur[0]
            version_installe = self.get_version_plugins(nom)
            item_version_installe = self.tablePlugins.item(row, 2)
            if item_version_installe is None:
                continue
            if version_installe is None:
                item_version_installe.setText("Non installé")
                item_version_installe.setBackground(QBrush(QColor(COLOR_NON_INSTALLE)))
            elif version_installe != version:
                item_version_installe.setText(version_installe)
                item_version_installe.setBackground(QBrush(QColor(COLOR_MAJ)))
            else:
                item_version_installe.setText(version_installe)
                item_version_installe.setBackground(QBrush(Qt.GlobalColor.white))

        log("Installation terminée")
        text = ("Installation terminé\n\n - Veuillez redémarrer QGIS pour prendre\n"
                "en compte les nouveaux plugins\n"
                " - Exécuter le 'plugin maitre' pour configurer les plugins")
        QMessageBox.information(self, "Installateur de plugins", text)

        progress.update(progress.getMaximum(),"Finalisation de l'installation")



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
        if self.ischeck:
            for row in range(self.tablePlugins.rowCount()):
                item = self.tablePlugins.item(row, 0)  # colonne Nom
                if self.tablePlugins.item(row, 0).text() != PLUGIN_MAITRE:
                        item.setCheckState(Qt.CheckState.Unchecked)
                        self.pushButton_tout_rien.setText("Tout sélectionner")
                        self.ischeck = False
        else:
            for row in range(self.tablePlugins.rowCount()):
                item = self.tablePlugins.item(row, 0)  # colonne Nom
                item.setCheckState(Qt.CheckState.Checked)
                self.pushButton_tout_rien.setText("Rien sélectionner")
                self.ischeck = True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = InstallerDialog()
    dlg.setWindowTitle(f"{TITRE}")
    log("Lancement de l'installateur",reset=True)

    # choix de la version de qgis (3 ou 4)
    # toutes les versions 3 partagent les meme profils
    path_qgis = Path(Path.home(), REP_QGIS)
    if not path_qgis.exists():
        QMessageBox.warning(None,"Avertissement",f"<b>Avertissement :</b><br><br>L'installation de QGIS n'a pas été trouvée.<br>Le répertoire  :<br><br><code>{path_qgis.as_posix()}</code><br><br>n'existe pas.")
        log(f"Le répertoire de QGIS : {path_qgis.as_posix()} -> n'existe pas.")
        sys.exit(1)

    rep_qgis = os.listdir(Path(Path.home(), REP_QGIS))
    text = ('<span style="font-weight:bold; color:blue;">Dans quelle version de QGIS souhaitez vous installer les plugins ? :</span><br><br>'
            "(QGIS3 pour toutes les versions 3.00 à 3.99)<br>"
            "(QGIS4 pour toutes les versions 4.00 à 4.99)<br>")
    dlg.dossier_qgis, ok = QInputDialog.getItem(dlg, "Choisir une version de QGIS", text,
                                                  rep_qgis, 0, False)
    log(f"La version de QGIS sélectionné est : {dlg.dossier_qgis}")
    if not ok:
        sys.exit(0)

    chemin_profils = Path.home() / "AppData"/"Roaming"/"QGIS"/dlg.dossier_qgis/"profiles"
    # Affichage dans QMessageBox : convertir en slash pour HTML
    chemin_profils_aff = chemin_profils.as_posix()
    if not os.path.exists(chemin_profils):
        QMessageBox.warning(None,"Avertissement",f"<b>Avertissement :</b><br>Aucun profil trouvé dans  :<br><br><code>{chemin_profils_aff}</code>")
        log(f"Le répertoire de QGIS : {chemin_profils_aff} -> n'existe pas.")
        sys.exit(1)
    # recuperation des différents profils de QGIS pour trouver le bon dossier d'installation des plugins
    rep_profils = [d.name for d in chemin_profils.iterdir() if d.is_dir()]
    if len(rep_profils) == 0 :
        QMessageBox.information(None,"Installateur de plugins","Aucun profil QGIS n'a été trouvé")
        log(f"aucun profil QGIS n'a été trouvé dans le répertoire : {chemin_profils_aff}")
        sys.exit(1)

    ok = True
    if len(rep_profils) == 1 and rep_profils[0] == "default":
        dlg.dossier_profil = "default"
    else:
        dlg.dossier_profil, ok = QInputDialog.getItem(dlg,"Choisir un profil QGIS",'<span style="font-weight:bold; color:blue;">Sélectionnez votre profil d\'installation :</span>',rep_profils,0,False)
        log(f"Le profil QGIS sélectionné est : {dlg.dossier_profil}")
    if not ok:
        sys.exit(0)

    rep_installe = dlg.get_rep_plugin_qgis()
    if not rep_installe:
        QMessageBox.warning(None, "Installateur de plugins", "Impossible de trouver le dossier d'installation des plugins QGIS")

    if dlg.initialiser_apres_profil():
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        dlg.exec()






