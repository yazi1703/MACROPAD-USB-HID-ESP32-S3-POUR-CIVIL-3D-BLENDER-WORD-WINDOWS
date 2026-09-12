# -*- coding: utf-8 -*-
"""
macropad_auto.py - Le compagnon Windows du macropad.

Ce programme tourne sur le PC, pas sur la carte. Il fait deux choses :

  1. DETECTION AUTOMATIQUE : il regarde toutes les 400 ms quelle
     application est au premier plan et dit au macropad quel profil
     activer. Tu passes sur Civil 3D, le macropad bascule tout seul.
     Il envoie aussi le nom du document, que l'ecran affiche.

  2. PAGE DE CONFIGURATION : il sert une page web sur
     http://127.0.0.1:8765 ou tu modifies tes macros a la souris. Les
     changements partent par le port serie et s'appliquent
     IMMEDIATEMENT, sans redemarrer le macropad.

=====================================================================
INSTALLATION
=====================================================================
    py -m pip install pyserial

Puis, dans une invite de commandes :

    py macropad_auto.py

Pour verifier que la detection marche sans avoir le macropad branche :

    py macropad_auto.py --simuler

=====================================================================
QUEL PORT SERIE ?
=====================================================================
La carte expose DEUX ports COM :
  * celui du pont USB-serie (CH343, CP210x...) -> reserve a Thonny
  * celui de l'USB natif de l'ESP32-S3         -> c'est celui-ci

Le script reconnait le second a son identifiant fabricant Espressif
(VID 0x303A) et le choisit tout seul. Tu peux forcer :

    py macropad_auto.py --port COM7

ATTENTION : un port serie ne s'ouvre qu'une fois. Si Thonny est connecte
au port NATIF, ce script ne pourra pas l'ouvrir. Garde Thonny sur le port
UART, c'est justement a ca qu'il sert.

=====================================================================
QUELS LOGICIELS ?
=====================================================================
La table des logiciels vit DANS LE MACROPAD. Tu la modifies dans la page
de configuration (http://127.0.0.1:8765), section "Logiciels detectes",
bouton "+ Logiciel". Trois colonnes :

    programme (.exe)     profil        abrege ecran
    acad.exe             CIVIL3D       C3D
    blender.exe          BLENDER       Blender
    winword.exe          WORD          Wrd

L'abrege est le petit texte fixe en bas a gauche de l'ecran, celui qui
reste lisible pendant que le nom du fichier defile a cote. Sept
caracteres au maximum : c'est la place disponible.

Tout ce qui n'est pas dans la liste prend la ligne "tout le reste"
(profil WINDOWS, abrege Win, par defaut).

Le fichier macropad_apps.txt, a cote de ce script, ne sert plus que de
SECOURS : il n'est consulte que si la carte ne repond pas, si tu lances
--simuler, ou tant que la table de la carte est vide. Meme principe, avec
un troisieme champ facultatif :

    acad.exe = CIVIL3D = C3D

Il est relu a chaud : pas besoin de relancer le script apres l'avoir
modifie.
"""

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER_APPS = os.path.join(DOSSIER, "macropad_apps.txt")
FICHIER_JOURNAL = os.path.join(DOSSIER, "macropad_auto.log")
JOURNAL_MAX = 200000    # octets : au-dela on repart d'un fichier vide
VID_ESPRESSIF = 0x303A
PORT_WEB = 8765
ABREGE_MAX = 7          # place disponible en bas a gauche de l'ecran
DOC_MAX = 48            # ce que l'ecran garde du nom de fichier
PERIODE_SYNC = 30.0     # on redemande la table des logiciels a la carte

APPS_PAR_DEFAUT = """# Association logiciel -> profil du macropad.
#
# ATTENTION : ce fichier n'est qu'un SECOURS. La vraie table est dans le
# macropad et se modifie dans la page de configuration
# (http://127.0.0.1:8765, section "Logiciels detectes"). Ce fichier n'est
# lu que si la carte ne repond pas, avec --simuler, ou tant que la table
# de la carte est vide.
#
# Une ligne par logiciel :
#     nom_du_programme.exe = NOM_DU_PROFIL = Abrege
#
# Le troisieme champ est facultatif : c'est le texte fixe affiche en bas
# a gauche de l'ecran (7 caracteres maximum) pendant que le nom du
# fichier defile. Sans lui, on reprend le nom du profil, coupe a 7.
#
# Les lignes vides et celles commencant par # sont ignorees.
# Ce fichier est relu automatiquement, inutile de relancer le script.

acad.exe = CIVIL3D = C3D
acadlt.exe = CIVIL3D = C3D
blender.exe = BLENDER = Blender
winword.exe = WORD = Wrd

# Quelques exemples a decommenter ou adapter :
# excel.exe = WORD = Xls
# qgis-bin.exe = QGIS = Qgis
# notepad.exe = WINDOWS = Win

# Profil utilise pour tout le reste :
* = WINDOWS = Win
"""


# =====================================================================
# 0. La seule dependance : pyserial
# =====================================================================
def verifier_pyserial():
    """Dit clairement quoi faire si pyserial manque. True = tout va bien.

    C'est LA erreur du premier lancement. Sans ce controle, Python affiche
    un « ModuleNotFoundError: No module named 'serial' » suivi de dix
    lignes de traceback, ce qui n'aide personne.
    """
    try:
        import serial               # noqa: F401
        return True
    except ImportError:
        pass
    print()
    print("=" * 62)
    print("  pyserial n'est pas installe : ce script ne peut pas parler")
    print("  au macropad sans lui.")
    print()
    print("  Ouvre une invite de commandes et tape :")
    print()
    print("      py -m pip install pyserial")
    print()
    print("  Puis relance ce script.")
    print()
    print("  Si « py » n'est pas reconnu, installe Python depuis")
    print("  python.org en COCHANT « Add Python to PATH ».")
    print()
    print("  Pour essayer la detection sans macropad et sans pyserial :")
    print("      py macropad_auto.py --simuler")
    print("=" * 62)
    print()
    return False


# =====================================================================
# 0 bis. Le journal : indispensable quand le script demarre tout seul
# =====================================================================
class _Double:
    """Ecrit a la fois dans la console et dans le fichier journal.

    Quand Windows lance ce script au demarrage, sa fenetre est reduite et
    tu ne la regardes jamais. Sans journal, une erreur passerait
    totalement inapercue. Avec, il te suffit d'ouvrir macropad_auto.log.
    """

    def __init__(self, console, fichier):
        self.console, self.fichier = console, fichier

    def write(self, texte):
        for sortie in (self.console, self.fichier):
            try:
                sortie.write(texte)
            except Exception:
                pass            # une console absente ne doit rien casser
        return len(texte)

    def flush(self):
        for sortie in (self.console, self.fichier):
            try:
                sortie.flush()
            except Exception:
                pass


def ouvrir_journal(chemin=FICHIER_JOURNAL):
    """Redirige l'affichage vers la console ET le fichier. Retourne le fichier."""
    try:
        if os.path.exists(chemin) and os.path.getsize(chemin) > JOURNAL_MAX:
            os.remove(chemin)       # on ne laisse pas grossir sans fin
        fichier = open(chemin, "a", encoding="utf-8", buffering=1)
    except OSError as exc:
        print("Journal impossible (%s), on continue sans." % exc)
        return None
    fichier.write("\n===== %s =====\n"
                  % time.strftime("%Y-%m-%d %H:%M:%S"))
    sys.stdout = _Double(sys.__stdout__, fichier)
    sys.stderr = _Double(sys.__stderr__, fichier)
    return fichier


# =====================================================================
# 1. Lire quelle application est au premier plan (API Windows)
# =====================================================================
class FenetreActive:
    """Interroge Windows sans dependance supplementaire, via ctypes."""

    def __init__(self):
        self.disponible = False
        if sys.platform != "win32":
            return
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.disponible = True

    def lire(self):
        """Retourne (nom_du_programme, titre_de_la_fenetre)."""
        if not self.disponible:
            return "", ""
        ctypes, wintypes = self.ctypes, self.wintypes
        fenetre = self.user32.GetForegroundWindow()
        if not fenetre:
            return "", ""

        # --- titre de la fenetre ---
        longueur = self.user32.GetWindowTextLengthW(fenetre)
        tampon = ctypes.create_unicode_buffer(longueur + 1)
        self.user32.GetWindowTextW(fenetre, tampon, longueur + 1)
        titre = tampon.value

        # --- nom de l'executable ---
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(fenetre, ctypes.byref(pid))
        # 0x1000 = PROCESS_QUERY_LIMITED_INFORMATION : le droit minimal,
        # il fonctionne sans etre administrateur.
        poignee = self.kernel32.OpenProcess(0x1000, False, pid.value)
        if not poignee:
            return "", titre
        try:
            chemin = ctypes.create_unicode_buffer(512)
            taille = wintypes.DWORD(512)
            self.kernel32.QueryFullProcessImageNameW(
                poignee, 0, chemin, ctypes.byref(taille))
            programme = os.path.basename(chemin.value)
        finally:
            self.kernel32.CloseHandle(poignee)
        return programme, titre


# =====================================================================
# 2. La table logiciel -> (profil, abrege)
# =====================================================================
def _abrege(texte, profil):
    """Nettoie un abrege, et en fabrique un si le champ est vide."""
    texte = (texte or "").strip()[:ABREGE_MAX]
    return texte or (profil or "")[:ABREGE_MAX]


class TableApplications:
    """Quel profil et quel abrege pour un programme donne ?

    Il y a DEUX sources possibles, et une seule sert a la fois :

      1. LE MACROPAD. La table est rangee dans la carte et se modifie
         dans la page de configuration. C'est la source normale : elle
         suit la carte, meme si tu la branches sur un autre PC.

      2. macropad_apps.txt, le fichier a cote de ce script. C'est le
         secours : carte muette, mode --simuler, ou table encore vide.

    On ne melange jamais les deux. Si la carte annonce au moins un
    logiciel, c'est elle qui decide et le fichier est ignore ; sinon
    c'est le fichier. Comme ca tu sais toujours ou regarder quand une
    detection ne fait pas ce que tu attends.
    """

    def __init__(self, chemin):
        self.chemin = chemin
        self.regles = {}                    # "acad.exe" -> ("CIVIL3D", "C3D")
        self.repli = ("WINDOWS", "Win")
        self.regles_carte = None            # None : la carte n'a rien dit
        self.repli_carte = None
        self._date = 0
        self._panne_signalee = False
        if not os.path.exists(chemin):
            with open(chemin, "w", encoding="utf-8") as fichier:
                fichier.write(APPS_PAR_DEFAUT)
            print("Table de secours creee :", chemin)
        self.recharger()

    # ------------------------------------------------------------------
    # Source 1 : la carte
    # ------------------------------------------------------------------
    def depuis_la_carte(self, bloc):
        """Range le bloc "apps" d'une configuration. Retourne True si ca change."""
        regles = {}
        for entree in (bloc or {}).get("liste", []):
            exe = str(entree.get("exe", "")).strip().lower()
            profil = str(entree.get("profil", "")).strip().upper()
            if not exe or not profil:
                continue                    # ligne a moitie remplie : on saute
            regles[exe] = (profil, _abrege(entree.get("abrege"), profil))
        bloc_repli = (bloc or {}).get("repli") or {}
        profil = str(bloc_repli.get("profil", "")).strip().upper() or "WINDOWS"
        repli = (profil, _abrege(bloc_repli.get("abrege"), profil))

        change = (regles, repli) != (self.regles_carte, self.repli_carte)
        self.regles_carte, self.repli_carte = regles, repli
        return change

    def synchroniser(self, macropad):
        """Va chercher la table sur la carte. Retourne False si elle se tait.

        Un echec n'est pas grave : on garde la table precedente, ou le
        fichier de secours. On ne le signale qu'une fois pour ne pas
        remplir la console de la meme phrase toutes les 30 secondes.
        """
        try:
            config = macropad.lire_config()
        except Exception as exc:
            if not self._panne_signalee:
                self._panne_signalee = True
                print("Table des logiciels : la carte ne repond pas (%s)." % exc)
                print("  -> on utilise", os.path.basename(self.chemin))
            return False
        self._panne_signalee = False
        if self.depuis_la_carte(config.get("apps")):
            if self.regles_carte:
                print("Table des logiciels lue sur le macropad : %d logiciels, "
                      "repli %s (%s)" % (len(self.regles_carte),
                                         self.repli_carte[0],
                                         self.repli_carte[1]))
            else:
                print("Le macropad ne connait aucun logiciel : on utilise",
                      os.path.basename(self.chemin))
        return True

    # ------------------------------------------------------------------
    # Source 2 : le fichier de secours
    # ------------------------------------------------------------------
    def recharger(self):
        """Relit macropad_apps.txt, mais seulement s'il a change."""
        try:
            date = os.path.getmtime(self.chemin)
        except OSError:
            return
        if date == self._date:
            return                          # rien de neuf, on ne fait rien
        self._date = date
        regles, repli = {}, ("WINDOWS", "Win")
        try:
            with open(self.chemin, encoding="utf-8") as fichier:
                for ligne in fichier:
                    ligne = ligne.strip()
                    if not ligne or ligne.startswith("#") or "=" not in ligne:
                        continue
                    # Deux ou trois champs : exe = PROFIL [= Abrege]
                    morceaux = [m.strip() for m in ligne.split("=", 2)]
                    cle = morceaux[0].lower()
                    profil = morceaux[1].upper()
                    if not profil:
                        continue            # "machin.exe =" tout seul
                    valeur = (profil, _abrege(morceaux[2] if len(morceaux) > 2
                                              else "", profil))
                    if cle == "*":
                        repli = valeur
                    else:
                        regles[cle] = valeur
        except OSError as exc:
            print("Table de secours illisible :", exc)
            return
        self.regles, self.repli = regles, repli
        print("Table de secours rechargee : %d regles, repli %s"
              % (len(regles), repli[0]))

    # ------------------------------------------------------------------
    def regle(self, programme):
        """Retourne (profil, abrege) pour ce programme."""
        if self.regles_carte:               # dictionnaire vide = pas de table
            return self.regles_carte.get((programme or "").lower(),
                                         self.repli_carte)
        return self.regles.get((programme or "").lower(), self.repli)

    def profil(self, programme):
        return self.regle(programme)[0]

    def abrege(self, programme):
        return self.regle(programme)[1]

    @property
    def source(self):
        return "macropad" if self.regles_carte else os.path.basename(self.chemin)


def nom_document(titre, programme=""):
    """Extrait un nom de document lisible du titre de la fenetre.

    Les titres Windows prennent deux formes principales :

        "Projet_A12.dwg - Autodesk Civil 3D 2024"     -> avant le tiret
        "Blender* [C:\\Travail\\maquette.blend]"      -> entre crochets

    On traite les crochets en premier (Blender, AutoCAD classique), puis
    le tiret. Si ce qui reste ressemble a un chemin, on ne garde que le
    nom du fichier : l'ecran n'a pas la place pour "C:\\Users\\...".

    On coupe a 48 caracteres, ce que l'ecran retient pour le defilement ;
    inutile d'envoyer plus, il n'en fera rien.
    """
    if not titre:
        return ""

    debut, fin = titre.rfind("["), titre.rfind("]")
    if 0 <= debut < fin:
        titre = titre[debut + 1:fin]
    else:
        for separateur in (" - ", " — ", " – ", " | "):
            if separateur in titre:
                titre = titre.split(separateur)[0]
                break

    for separateur in ("\\", "/"):        # chemin complet -> nom du fichier
        if separateur in titre:
            titre = titre.rsplit(separateur, 1)[-1]

    titre = titre.strip().strip("*").strip()       # * = document modifie
    return titre[:DOC_MAX]


# =====================================================================
# 3. Le dialogue avec le macropad
# =====================================================================
class Macropad:
    """Port serie vers la carte, protege par un verrou.

    Le fil de la detection et celui du serveur web s'en servent tous les
    deux : le verrou garantit qu'un echange de configuration n'est pas
    coupe en deux par un envoi de profil.
    """

    def __init__(self, port=None, simuler=False):
        self.simuler = simuler
        self.port_demande = port      # ce que tu as impose avec --port
        self.port = port
        self.serie = None
        self.verrou = threading.Lock()
        self.generation = 0           # +1 a chaque (re)connexion reussie
        self._absence_signalee = False
        # La RAISON de l'absence, pas seulement le fait. Sans elle, la page
        # web affiche "macropad non connecte" et te laisse deviner entre
        # trois causes tres differentes.
        self.raison_absence = "pas encore de tentative de connexion"

    def _sans_carte(self):
        """Le message a montrer quand la carte manque, raison comprise."""
        return "macropad non connecte : " + self.raison_absence
        if not simuler:
            # On n'abandonne PAS si la carte n'est pas la : au demarrage de
            # Windows, ce script peut partir avant que l'USB du macropad
            # soit reconnu. On attend, et on se connecte des qu'il arrive.
            self.assurer()

    # ------------------------------------------------------------------
    @staticmethod
    def trouver_port():
        """Cherche le port USB natif de l'ESP32-S3 (fabricant Espressif)."""
        try:
            from serial.tools import list_ports
        except ImportError:
            return None
        candidats = []
        for infos in list_ports.comports():
            if infos.vid == VID_ESPRESSIF:
                candidats.append(infos.device)
        if candidats:
            return candidats[0]
        return None

    def assurer(self):
        """Ouvre le port si ce n'est pas deja fait. True = on est connecte.

        Cette methode ne leve jamais d'exception : elle est appelee a chaque
        tour de boucle, et l'absence du macropad est une situation normale
        (pas encore branche, debranche, ou Thonny qui tient le port).
        """
        if self.simuler or self.serie is not None:
            return True
        try:
            import serial
        except ImportError:
            self._signaler_absence("pyserial n'est pas installe "
                                   "(py -m pip install pyserial).")
            return False
        port = self.port_demande or self.trouver_port()
        if port is None:
            self._signaler_absence(
                "Macropad absent : aucun port Espressif (VID 0x303A) trouve.")
            return False
        try:
            self.serie = serial.Serial(port, 115200, timeout=0.3)
        except Exception as exc:
            self._signaler_absence("Port %s indisponible (%s)." % (port, exc))
            return False
        self.port = port
        self.generation += 1
        self._absence_signalee = False
        print("Macropad connecte sur", port)
        return True

    # Ancien nom, garde parce qu'il est explicite dans les traces.
    ouvrir = assurer

    def _signaler_absence(self, message):
        """Ne se plaint qu'une fois : ce script tourne peut-etre toute la
        journee, il ne doit pas remplir la console de la meme phrase.

        La raison est MEMORISEE meme quand on ne la reimprime pas : la page
        web la redemande a chaque rafraichissement.
        """
        self.raison_absence = message
        if self._absence_signalee:
            return
        self._absence_signalee = True
        print(message)
        print("  On attend qu'il soit branche (port USB NATIF).")
        print("  Si Thonny est connecte a ce port, deconnecte-le.")
        print("  Ctrl-C pour arreter.")

    def _perdu(self, exc):
        """Le cable a ete debranche, ou la carte a redemarre."""
        try:
            if self.serie is not None:
                self.serie.close()
        except Exception:
            pass
        self.serie = None
        self._absence_signalee = False
        self.raison_absence = "cable debranche ou carte redemarree (%s)" % exc
        print("Macropad deconnecte (%s). On attend son retour." % exc)

    # ------------------------------------------------------------------
    def _ecrire(self, ligne):
        if self.simuler:
            print("  -> %s" % ligne)
            return
        try:
            self.serie.write((ligne + "\n").encode())
        except Exception as exc:
            self._perdu(exc)
            raise

    def envoyer(self, ligne):
        with self.verrou:
            if not self.assurer():
                return False
            try:
                self._ecrire(ligne)
            except Exception:
                return False        # _perdu a deja explique ce qui se passe
            return True

    def _lire_reponse(self, fin, delai=3.0):
        """Lit jusqu'au marqueur de fin. Ignore les messages de debogage."""
        if self.simuler:
            return []
        lignes = []
        limite = time.time() + delai
        while time.time() < limite:
            try:
                brut = self.serie.readline()
            except Exception as exc:
                self._perdu(exc)
                raise
            if not brut:
                continue
            ligne = brut.decode("utf-8", "replace").strip()
            if not ligne.startswith("#"):
                continue          # trace normale du firmware, pas pour nous
            if ligne == fin:
                return lignes
            lignes.append(ligne)
        raise TimeoutError("le macropad n'a pas repondu (%s)" % fin)

    # ------------------------------------------------------------------
    def lire_config(self):
        """Demande la configuration complete au macropad."""
        with self.verrou:
            if self.simuler:
                # Table vide : le mode --simuler se rabat volontairement
                # sur macropad_apps.txt, qu'on peut ainsi tester sans carte.
                return {"ordre": [], "profils": {}, "touches": 6,
                        "apps": {"repli": {"profil": "WINDOWS",
                                           "abrege": "Win"},
                                 "liste": []},
                        "origine": "simulation"}
            if not self.assurer():
                raise IOError(self._sans_carte())
            self.serie.reset_input_buffer()
            self._ecrire("?CFG")
            self._lire_reponse("#CFGBEGIN")
            morceaux = self._lire_reponse("#CFGEND")
        texte = "".join(m[3:] for m in morceaux if m.startswith("#C:"))
        return json.loads(texte)

    def compteurs_a_zero(self):
        """Demande au macropad d'effacer ses compteurs d'usage.

        Ils vivent SUR LA CARTE, pas sur le PC : c'est elle qui compte les
        appuis, et c'est donc a elle de les oublier.
        """
        with self.verrou:
            if self.simuler:
                self._ecrire("!ZERO")
                return True, ""
            if not self.assurer():
                return False, self._sans_carte()
            try:
                self.serie.reset_input_buffer()
                self._ecrire("!ZERO")
            except Exception as exc:
                return False, "macropad deconnecte (%s)" % exc
            limite = time.time() + 3.0
            while time.time() < limite:
                try:
                    brut = self.serie.readline()
                except Exception as exc:
                    self._perdu(exc)
                    return False, "macropad deconnecte (%s)" % exc
                if not brut:
                    continue
                ligne = brut.decode("utf-8", "replace").strip()
                if ligne.startswith("#OK:"):
                    return True, ""
                if ligne.startswith("#KO:"):
                    return False, ligne[4:]
        return False, "le macropad n'a pas confirme"

    def ecrire_config(self, data):
        """Envoie une configuration. Retourne (True, "") ou (False, raison)."""
        texte = json.dumps(data)
        with self.verrou:
            if self.simuler:
                self._ecrire("!CFGBEGIN ... %d octets ... !CFGEND" % len(texte))
                return True, ""
            if not self.assurer():
                return False, self._sans_carte()
            try:
                self.serie.reset_input_buffer()
                self._ecrire("!CFGBEGIN")
                for debut in range(0, len(texte), 160):
                    self._ecrire("!C:" + texte[debut:debut + 160])
                self._ecrire("!CFGEND")
            except Exception as exc:
                return False, "macropad deconnecte (%s)" % exc
            limite = time.time() + 5.0
            while time.time() < limite:
                try:
                    brut = self.serie.readline()
                except Exception as exc:
                    self._perdu(exc)
                    return False, "macropad deconnecte (%s)" % exc
                if not brut:
                    continue
                ligne = brut.decode("utf-8", "replace").strip()
                if ligne.startswith("#OK:"):
                    return True, ""
                if ligne.startswith("#KO:"):
                    return False, ligne[4:]
        return False, "le macropad n'a pas confirme"


# =====================================================================
# 4. La page de configuration, servie sur http://127.0.0.1:8765
# =====================================================================
# Note : cette page est volontairement proche de celle de device/portal.py.
# Les deux existent parce qu'elles servent des cas differents : celle-ci
# passe par le cable USB, l'autre par le WiFi depuis un telephone.
PAGE = r"""<!DOCTYPE html><html lang=fr><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Macropad</title><style>
*{box-sizing:border-box}
body{margin:0;padding:0 0 40px;background:#0e1014;color:#e8eaee;
font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{position:sticky;top:0;z-index:9;background:#151922;
border-bottom:1px solid #262c3a;padding:14px 18px;display:flex;
align-items:center;gap:14px;flex-wrap:wrap}
header h1{font-size:16px;margin:0;letter-spacing:.4px}
header .tag{font:11px ui-monospace,monospace;color:#8b94a6;
border:1px solid #2b3242;border-radius:99px;padding:3px 9px}
main{max-width:940px;margin:0 auto;padding:18px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:1px;
color:#8b94a6;margin:26px 0 10px;font-weight:600}
.card{background:#151922;border:1px solid #262c3a;border-radius:12px;
padding:14px;margin-bottom:12px}
.ph{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
.ph .grow{flex:1;min-width:110px}
input,select{background:#0b0d12;color:#e8eaee;border:1px solid #2b3242;
border-radius:7px;padding:7px 9px;font:13px/1.2 ui-monospace,monospace;
width:100%}
input[type=color]{width:42px;flex:0 0 42px;padding:2px;height:33px;
cursor:pointer}
.val{display:flex;gap:5px;align-items:center}
.pile{display:flex;flex-direction:column;gap:5px}
.pile select{flex:0 0 138px}
.pile .add{align-self:flex-start;padding:4px 9px;font-size:11px}
.cap{flex:0 0 30px;padding:6px 0;font-size:14px;line-height:1}
.cap.on{background:#3d7bfd;color:#fff}
.rec{color:#f0a6b6}
.rec.on{background:#6d2233;color:#fff}
#msg.rec{background:#33131d;border:1px solid #7d2a3c;color:#f0a6b6}
input:focus,select:focus{outline:0;border-color:#3d7bfd}
table{width:100%;border-collapse:collapse}
td,th{padding:3px 5px 3px 0;vertical-align:middle}
th{font:11px system-ui;color:#6f7788;text-align:left;font-weight:600;
text-transform:uppercase;letter-spacing:.6px;padding-bottom:6px}
td.k{width:30px;color:#3d7bfd;font:700 13px ui-monospace,monospace}
td.g{width:58px;color:#6f7788;font:11px system-ui}
td.lab{width:110px}td.ty{width:132px}
tr.sep td{border-top:1px solid #1f2531;padding-top:8px}
.use{width:64px;text-align:right;font:11px ui-monospace,monospace;color:#6f7788}
.bar{height:3px;background:#3d7bfd;border-radius:2px;margin-top:3px}
button{background:#2b3242;color:#e8eaee;border:0;border-radius:8px;
padding:9px 14px;font:600 13px system-ui;cursor:pointer}
button:hover{filter:brightness(1.25)}
button.p{background:#3d7bfd;color:#fff}button.d{background:#6d2233}
button.s{padding:6px 10px;font-size:12px}
.bar2{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
#msg{margin-top:16px;padding:11px 13px;border-radius:9px;display:none;
white-space:pre-wrap;font:13px ui-monospace,monospace}
.ok{background:#0f2e20;border:1px solid #1d6f47;color:#8ee0b4}
.ko{background:#33131d;border:1px solid #7d2a3c;color:#f0a6b6}
.hint{color:#6f7788;font-size:12px;margin:0 0 14px}
.combos{margin-top:14px;border-top:1px solid #1f2531;padding-top:12px}
.combos h3{font:600 11px system-ui;text-transform:uppercase;
letter-spacing:.6px;color:#6f7788;margin:0 0 8px}
.combos .hint{margin:0 0 8px}
td.duo{width:78px}
td.duo input{color:#3d7bfd;font:700 13px ui-monospace,monospace;
text-align:center}
.vide{text-align:center;padding:26px 14px}
.vide b{display:block;font-size:15px;margin-bottom:8px;color:#e8eaee}
.vide p{color:#8b94a6;margin:5px 0;font-size:13px}
</style></head><body>
<header>
<h1>Macropad</h1>
<span class=tag id=src>...</span>
<span class=tag id=cnt>...</span>
</header>
<main>
<p class=hint>Libelles : 6 caracteres maximum. Combinaison :
<b>CTRL+MAJ+ESC</b>. Chaque touche accepte trois gestes : appui court,
appui long et double appui.</p>
<p class=hint>Le carre de couleur a cote du titre donne la couleur des
LED RGB de ce profil. Comme le PC change de profil selon le logiciel au
premier plan, <b>le macropad prend la couleur du logiciel</b> ou tu
travailles, en respiration douce.</p>
<p class=hint>Un geste peut <b>enchainer plusieurs etapes</b> :
« + etape » ajoute une ligne. Utile quand un logiciel a besoin de
respirer entre deux frappes — tape la commande, mets une
<b>pause</b> de 500 ms, puis valide.</p>
<p class=hint><b>maintenir</b> transforme la touche en vraie touche
modificatrice : mets <b>CTRL</b> sur l'appui court et <b>MAJ</b> sur le
double appui, et tu obtiens <i>appui maintenu = Ctrl</i>,
<i>appui bref puis maintenu = Maj</i>. Le modificateur reste enfonce tant
que ton doigt reste sur la touche, ce qui permet de cliquer a la souris
pendant ce temps.</p>

<h2>Profils et macros</h2>
<div id=profs></div>
<div class=bar2><button class=s onclick=addProfil()>+ Profil</button></div>

<h2>Logiciels detectes</h2>
<p class=hint>Le compagnon PC lit cette table sur le macropad. Le nom
abrege reste affiche a gauche de l'ecran pendant que le nom du fichier
defile.</p>
<div class=card id=apps></div>

<div class=bar2>
<button class=p onclick=save()>Enregistrer</button>
<button onclick=dl()>Telecharger la sauvegarde</button>
<button onclick=restaurer()>Restaurer une sauvegarde</button>
<button onclick=zero()>Compteurs a zero</button>
<button class=d onclick=usine()>Valeurs d'usine</button>
</div>
<div id=msg></div>
</main>
<script>
// =====================================================================
// LE FILET : UNE PAGE NE DOIT JAMAIS MOURIR EN SILENCE
// =====================================================================
// En JavaScript, une seule erreur arrete TOUT le script. La page s'affiche
// alors - le HTML est deja la - mais plus rien ne repond : ni bouton, ni
// tableau, et pas le moindre message. C'est arrive deux fois dans ce
// projet (corrections 11 et 13), et les deux fois il a fallu deviner.
//
// Ce gestionnaire est donc la PREMIERE chose du script : tout ce qui suit
// est couvert. Une erreur s'affiche desormais a l'ecran, avec sa ligne.
window.onerror=function(message,source,ligne,colonne){
 try{
  var m=document.getElementById("msg");
  if(m){
   m.className="ko";m.style.display="block";
   m.textContent="La page a rencontre une erreur JavaScript et s'est "+
    "arretee :\n\n"+message+"\n(ligne "+ligne+", colonne "+colonne+")"+
    "\n\nRien n'a ete envoye au macropad. Recharge la page ; si ca "+
    "recommence, signale ce message tel quel.";}
 }catch(e){}
 return false;};

var D={ordre:[],profils:{},apps:{repli:{profil:"WINDOWS",abrege:"Win"},liste:[]}};
var N=6,GESTES=["court","long","double"];
var LIB={court:"court",long:"long",double:"double"};
var TYPES=[["none","inactive"],["key","touche"],["combo","combinaison"],
["maintien","maintenir (Ctrl, Maj...)"],
["text","texte"],["text_enter","texte + Entree"],
["pause","pause (millisecondes)"]];

function el(tag,attrs,kids){var e=document.createElement(tag);
 for(var k in attrs||{}){if(k=="cls")e.className=attrs[k];
  else if(k.slice(0,2)=="on")e[k]=attrs[k];else e.setAttribute(k,attrs[k]);}
 (kids||[]).forEach(function(c){
  e.appendChild(typeof c=="string"?document.createTextNode(c):c);});
 return e;}
// fin=true : on previent quand tu QUITTES le champ, pas a chaque
// frappe. Indispensable pour le nom d'un profil, qui redessine la page.
// Le selecteur de couleur du navigateur : c'est lui qui pilote la
// couleur des LED RGB du profil. Il rend une valeur du genre "#00a0ff".
function col(val,cb){var i=el("input",{type:"color"});
 i.value=val||"#808080";i.title="couleur des LED de ce profil";
 i.oninput=function(){cb(i.value);};return i;}

function inp(val,max,cb,fin){var i=el("input");i.value=val||"";
 if(max)i.maxLength=max;
 if(fin)i.onchange=function(){cb(i.value);};
 else i.oninput=function(){cb(i.value);};
 return i;}
function sel(val,cb){var s=el("select");TYPES.forEach(function(t){
 var o=el("option",{value:t[0]},[t[1]]);if(t[0]==val)o.selected=true;
 s.appendChild(o);});s.onchange=function(){cb(s.value);render();};return s;}

// =====================================================================
// CAPTURE D'UN RACCOURCI
// =====================================================================
// Plutot que de deviner comment s'ecrit une touche (SUPPR ? DELETE ?
// PAGEDOWN ?), tu cliques sur le bouton et tu APPUIES sur la combinaison.
// On lit ev.code, c'est-a-dire la touche PHYSIQUE : le resultat ne depend
// donc pas de la disposition du clavier, exactement comme le firmware qui
// raisonne lui aussi en touches physiques.
var TOUCHES={Escape:"ESC",Tab:"TAB",Space:"SPACE",Enter:"ENTER",
NumpadEnter:"ENTER",Backspace:"BACKSPACE",Delete:"SUPPR",Insert:"INSERT",
Home:"HOME",End:"END",PageUp:"PAGEUP",PageDown:"PAGEDOWN",
ArrowUp:"UP",ArrowDown:"DOWN",ArrowLeft:"LEFT",ArrowRight:"RIGHT",
PrintScreen:"PRINTSCREEN",ContextMenu:"MENU",CapsLock:"CAPSLOCK"};
var MODIFS={ControlLeft:"CTRL",ControlRight:"CTRL",ShiftLeft:"SHIFT",
ShiftRight:"SHIFT",AltLeft:"ALT",AltRight:"ALTGR",MetaLeft:"WIN",
MetaRight:"WIN"};

function nomTouche(ev){
 var code=ev.code||"";
 // AltGr se presente comme Ctrl+Alt sous Windows : on le detecte a part.
 var altgr=(code=="AltRight")||
  (ev.getModifierState&&ev.getModifierState("AltGraph"));
 if(MODIFS[code])return altgr?"ALTGR":MODIFS[code];

 var base="";
 if(code.slice(0,3)=="Key")base=code.slice(3);
 else if(code.slice(0,5)=="Digit")base=code.slice(5);
 else if(code.slice(0,6)=="Numpad"&&TOUCHES[code])base=TOUCHES[code];
 else if(code.charAt(0)=="F"&&code.length<=3&&!isNaN(code.slice(1)))base=code;
 else if(TOUCHES[code])base=TOUCHES[code];
 if(!base)return "";

 var parties=[];
 if(altgr)parties.push("ALTGR");
 else{if(ev.ctrlKey)parties.push("CTRL");if(ev.altKey)parties.push("ALT");}
 if(ev.shiftKey)parties.push("SHIFT");
 if(ev.metaKey)parties.push("WIN");
 parties.push(base);
 return parties.join("+");}

function capture(champ,cb){
 var b=el("button",{cls:"s cap",
  title:"Cliquer, puis appuyer sur la combinaison voulue"},["\u2328"]);
 b.onclick=function(){
  b.className="s cap on";champ.value="";
  champ.onkeydown=function(ev){
   var nom=nomTouche(ev);
   if(!nom)return;
   if(ev.preventDefault)ev.preventDefault();
   champ.value=nom;cb(nom);
   champ.onkeydown=null;b.className="s cap";};
  if(champ.focus)champ.focus();};
 return b;}

// =====================================================================
// L'ENREGISTREUR DE SEQUENCE
// =====================================================================
// Tu cliques sur Enregistrer, tu tapes ta sequence au clavier, et la page
// la transforme en etapes. Beaucoup plus rapide que de choisir un type et
// une valeur pour chaque frappe - et surtout, ca capture les PAUSES
// REELLES, celles qu'on ne pense jamais a mesurer soi-meme.
//
// Trois regles, et elles suffisent a couvrir presque tout :
//
//   1. les caracteres ordinaires s'ACCUMULENT : "_PLINE" fait UNE etape
//      de type texte, pas six etapes de type touche ;
//   2. Entree juste apres du texte transforme l'etape en "texte + Entree",
//      exactement l'idiome des commandes AutoCAD ;
//   3. tout ce qui porte Ctrl, Alt ou Win, et toute touche speciale,
//      ferme le texte en cours et devient sa propre etape.
var REC = null;          // {k:objet, g:geste, texte:"", t:instant}
var REC_PAUSE_MIN = 400; // en dessous, on ne note pas de pause
var REC_PAUSE_MAX = 5000;// PAUSE_MAX_MS du firmware

// etapes() recree un emplacement vide des que la liste l'est - c'est ce
// qui affiche une ligne prete a remplir. Pendant un enregistrement, cet
// emplacement deviendrait une etape "inactive" en tete de sequence : on
// le retire a la premiere vraie frappe.
function recListe(){
 var liste=REC.k[REC.g];
 while(liste.length&&liste[0].type=="none"&&!liste[0].valeur)liste.shift();
 return liste;}

function recVider(){
 if(REC&&REC.texte){
  recListe().push({type:"text",valeur:REC.texte});
  REC.texte="";}}

function recPause(maintenant){
 if(!REC.t)return;
 var ecart=maintenant-REC.t;
 if(ecart<REC_PAUSE_MIN)return;
 if(!recListe().length&&!REC.texte)return;    // rien avant : pas de pause
 recVider();
 var ms=Math.round(ecart/50)*50;
 if(ms>REC_PAUSE_MAX)ms=REC_PAUSE_MAX;
 recListe().push({type:"pause",valeur:String(ms)});}

function recTouche(ev){
 if(!REC)return true;
 if(MODIFS[ev.code])return true;          // Ctrl seul : on attend la suite
 if(ev.preventDefault)ev.preventDefault();
 var seul=!ev.ctrlKey&&!ev.altKey&&!ev.metaKey;
 if(ev.code=="Escape"&&seul){recStop();return false;}
 var maintenant=Date.now();
 recPause(maintenant);
 if(seul&&ev.key&&ev.key.length==1){
  REC.texte+=ev.key;                      // un caractere ordinaire
 }else if(seul&&ev.code=="Enter"&&REC.texte){
  recListe().push({type:"text_enter",valeur:REC.texte});
  REC.texte="";
 }else{
  recVider();
  var nom=nomTouche(ev);
  if(!nom)return false;
  recListe().push({type:nom.indexOf("+")>=0?"combo":"key",valeur:nom});}
 REC.t=maintenant;
 render();
 return false;}

function recDemarrer(k,g){
 if(REC)recStop();
 k[g]=[];                                 // on REMPLACE, on n'ajoute pas
 REC={k:k,g:g,texte:"",t:0};
 if(document.activeElement&&document.activeElement.blur)
  document.activeElement.blur();
 document.onkeydown=recTouche;
 render();
 say("Enregistrement : tape ta sequence au clavier. Echap ou le bouton "+
  "Stop pour terminer. Les attentes de plus de 0,4 s deviennent des "+
  "pauses. Rien n'est envoye au macropad avant Enregistrer.",1);
 var boite=document.getElementById("msg");
 if(boite)boite.className="rec";}

function recStop(){
 if(!REC)return;
 recVider();
 var combien=recListe().length;
 document.onkeydown=null;
 REC=null;
 render();
 say(combien?("Enregistre : "+combien+" etape(s). Verifie, puis clique "+
  "sur Enregistrer pour l'appliquer au macropad."):
  "Rien n'a ete enregistre.",1);}

// Le meme bouton sert aux gestes et aux combinaisons : les deux rangent
// leurs etapes dans la meme forme.
function boutonEnr(k,g){
 var actif=REC&&REC.k===k&&REC.g===g;
 return el("button",{cls:actif?"s add rec on":"s add rec",
  title:actif?"Terminer l'enregistrement":
   "Enregistrer la sequence au clavier (remplace les etapes)"},
  [actif?"\u25a0 Stop":"\u23fa Enregistrer"]);}

function maxUse(){var m=1;for(var n in D.profils)
 (D.profils[n].touches||[]).forEach(function(t){if(t.usages>m)m=t.usages;});
 return m;}

function vide(){
 var c=el("div",{cls:"card vide"},[]);
 c.appendChild(el("b",{},["Aucun profil recu du macropad."]));
 if(D.origine=="simulation"){
  c.appendChild(el("p",{},["Le compagnon tourne en mode --simuler : il "+
   "n'est relie a aucune carte."]));
  c.appendChild(el("p",{},["Relance-le sans --simuler, macropad branche."]));
 }else{
  c.appendChild(el("p",{},["1. Le macropad est-il branche sur son port "+
   "USB NATIF (celui marque USB, pas COM/UART) ?"]));
  c.appendChild(el("p",{},["2. Thonny est-il connecte a ce port ? Il le "+
   "garde pour lui : clique sur STOP, ou ferme Thonny."]));
  c.appendChild(el("p",{},["3. Le firmware tourne-t-il normalement ? En "+
   "SAFE MODE (B1 au RESET) et en MODE CONFIG (B2 au RESET), la liaison "+
   "serie n'existe pas."]));
  c.appendChild(el("p",{},["La console du compagnon dit ce qu'elle voit ; "+
   "avec --journal, tout est dans macropad_auto.log."]));
 }
 c.appendChild(el("p",{},["Tu peux aussi partir des valeurs d'usine avec le "+
  "bouton rouge, ou ajouter un profil ci-dessous."]));
 return c;}

// Une fonction a part, et ce n'est pas cosmetique : en JavaScript,
// « var » appartient a la FONCTION, pas au bloc. Ecrite dans la boucle,
// la variable k etait la MEME pour les six touches, si bien que tous les
// champs finissaient par ecrire dans la derniere. Ici chaque appel a sa
// propre variable k : chaque champ modifie bien sa touche.
// Un geste est une SUITE d'etapes : taper une commande, attendre que la
// boite de dialogue s'ouvre, valider. Une seule etape reste le cas
// courant, et c'est ce qu'on affiche par defaut.
function etapes(k,g){
 if(!k[g]||!k[g].length)k[g]=[{type:"none",valeur:""}];
 else if(!k[g].length&&k[g].type)k[g]=[k[g]];   // ancienne forme
 return k[g];}

function ligneEtape(k,g,i){
 var e=k[g][i];
 var l=el("div",{cls:"val"},[]);
 l.appendChild(sel(e.type,function(v){e.type=v;}));
 var champ=inp(e.valeur,60,function(v){e.valeur=v;});
 if(e.type=="pause")champ.title="duree en millisecondes, 500 par exemple";
 l.appendChild(champ);
 if(e.type=="key"||e.type=="combo"||e.type=="maintien")
  l.appendChild(capture(champ,function(v){e.valeur=v;}));
 if(k[g].length>1)
  l.appendChild(el("button",{cls:"d s cap",title:"retirer cette etape",
   onclick:function(){k[g].splice(i,1);render();}},["\u00d7"]));
 return l;}

function ligne(p,i,tb,mx){
 if(!p.touches[i])p.touches[i]={label:"",usages:0};
 var k=p.touches[i];
 GESTES.forEach(function(g,gi){
  var tr=el("tr",{cls:gi==0?"sep":""},[]);
  if(gi==0)tr.appendChild(el("td",{cls:"k",rowspan:3},["B"+(i+1)]));
  tr.appendChild(el("td",{cls:"g"},[LIB[g]]));
  if(gi==0){
   var cl=el("td",{cls:"lab",rowspan:3},[]);
   cl.appendChild(inp(k.label,6,function(v){k.label=v;}));
   tr.appendChild(cl);
  }
  var ca=el("td",{},[]);
  var pile=el("div",{cls:"pile"},[]);
  etapes(k,g).forEach(function(e,rang){
   pile.appendChild(ligneEtape(k,g,rang));});
  pile.appendChild(el("button",{cls:"s add",title:"enchainer une etape",
   onclick:function(){k[g].push({type:"none",valeur:""});render();}},
   ["+ etape"]));
  var enr=boutonEnr(k,g);
  enr.onclick=function(){
   if(REC&&REC.k===k&&REC.g===g)recStop();else recDemarrer(k,g);};
  pile.appendChild(enr);
  ca.appendChild(pile);
  tr.appendChild(ca);
  if(gi==0){
   var u=k.usages||0;
   var box=el("td",{cls:"use",rowspan:3},[String(u)]);
   var b=el("div",{cls:"bar"});b.style.width=Math.round(60*u/mx)+"px";
   box.appendChild(b);tr.appendChild(box);
  }
  tb.appendChild(tr);
 });
}

// =====================================================================
// LES COMBINAISONS : DEUX TOUCHES APPUYEES ENSEMBLE
// =====================================================================
// Elles se rangent sous le tableau du profil, et leurs actions se
// modifient avec le MEME editeur d'etapes que les gestes : rien de neuf
// a apprendre, et rien de neuf a maintenir non plus.
//
// Les numeros sont ceux qui sont graves sur le pad : on ecrit 3+4 pour
// B3 et B4. La conversion vers les indices internes est faite par la
// carte, pas ici.
function litTouches(v){
 var out=[];
 (v||"").split(/[^0-9]+/).forEach(function(m){
  var n=parseInt(m,10);
  if(n>=1&&n<=N&&out.indexOf(n)<0)out.push(n);});
 out.sort(function(a,b){return a-b;});
 return out;}

// Une fonction a part, comme ligne() : sinon la variable de boucle serait
// partagee par toutes les lignes et chaque champ ecrirait dans la
// derniere combinaison.
function ligneCombo(liste,ci,tb){
 var c=liste[ci];
 var tr=el("tr",{},[]);
 var ct=inp((c.touches||[]).join("+"),11,
  function(v){c.touches=litTouches(v);},true);
 ct.title="numeros des touches appuyees ensemble, par exemple 3+4";
 var c1=el("td",{cls:"duo"},[]);c1.appendChild(ct);tr.appendChild(c1);
 var cl=inp(c.label,16,function(v){c.label=v;});
 cl.title="libelle affiche a l'ecran quand la combinaison part";
 var c2=el("td",{cls:"lab"},[]);c2.appendChild(cl);tr.appendChild(c2);
 var pile=el("div",{cls:"pile"},[]);
 etapes(c,"actions").forEach(function(e,rang){
  pile.appendChild(ligneEtape(c,"actions",rang));});
 pile.appendChild(el("button",{cls:"s add",title:"enchainer une etape",
  onclick:function(){c.actions.push({type:"none",valeur:""});render();}},
  ["+ etape"]));
 var enr=boutonEnr(c,"actions");
 enr.onclick=function(){
  if(REC&&REC.k===c&&REC.g==="actions")recStop();else recDemarrer(c,"actions");};
 pile.appendChild(enr);
 var c3=el("td",{},[]);c3.appendChild(pile);tr.appendChild(c3);
 tr.appendChild(el("td",{cls:"use"},[el("button",{cls:"d s",
  title:"supprimer cette combinaison",
  onclick:function(){liste.splice(ci,1);render();}},["x"])]));
 tb.appendChild(tr);}

function tableauCombos(p){
 // On ne cree PAS p.combos quand il manque : une liste vide veut dire
 // "aucune combinaison" et effacerait celles d'usine. Elle n'apparait
 // donc que si tu cliques sur le bouton.
 var liste=p.combos||[];
 var bloc=el("div",{cls:"combos"},[
  el("h3",{},["Combinaisons - deux touches appuyees ensemble"])]);
 if(!p.combos)bloc.appendChild(el("p",{cls:"hint"},
  ["Cette sauvegarde est anterieure aux combinaisons : celles d'usine "+
   "seront reprises. Ajoutes-en une ici pour decider toi-meme."]));
 var tb=el("table",{},[el("tr",{},[el("th",{},["Touches"]),
  el("th",{},["Libelle"]),el("th",{},["Action"]),el("th",{},[""])])]);
 for(var i=0;i<liste.length;i++)ligneCombo(liste,i,tb);
 bloc.appendChild(tb);
 bloc.appendChild(el("button",{cls:"s add",onclick:function(){
  if(!p.combos)p.combos=[];
  p.combos.push({touches:[],label:"",actions:[]});render();}},
  ["+ combinaison"]));
 return bloc;}

function render(){
 var zone=document.getElementById("profs");zone.innerHTML="";
 var mx=maxUse();
 if(!D.ordre.length){zone.appendChild(vide());renderApps();return;}
 D.ordre.forEach(function(nom){
  var p=D.profils[nom];if(!p)return;
  var head=el("div",{cls:"ph"},[]);
  head.appendChild(inp(nom,20,function(v){ren(nom,v);},true));
  head.firstChild.className="grow";head.firstChild.title="nom interne";
  var t=inp(p.titre,16,function(v){p.titre=v;});t.className="grow";
  t.title="titre affiche sur l'ecran";head.appendChild(t);
  head.appendChild(col(p.couleur,function(v){p.couleur=v;}));
  head.appendChild(el("button",{cls:"d s",onclick:function(){del(nom);}},
   ["Supprimer"]));
  var tb=el("table",{},[el("tr",{},[el("th",{},["#"]),el("th",{},["Geste"]),
   el("th",{},["Libelle"]),el("th",{},["Action"]),
   el("th",{},["Usage"])])]);
  for(var i=0;i<N;i++)ligne(p,i,tb,mx);
  zone.appendChild(el("div",{cls:"card"},[head,tb,tableauCombos(p)]));
 });
 renderApps();
}

function renderApps(){
 var z=document.getElementById("apps");z.innerHTML="";
 var tb=el("table",{},[el("tr",{},[el("th",{},["Programme (.exe)"]),
  el("th",{},["Profil"]),el("th",{},["Abrege ecran"]),el("th",{},[""])])]);
 D.apps.liste.forEach(function(a,i){
  var tr=el("tr",{},[]);
  var c1=el("td",{},[]);c1.appendChild(inp(a.exe,40,function(v){a.exe=v;}));
  var c2=el("td",{},[]);c2.appendChild(inp(a.profil,20,function(v){a.profil=v;}));
  var c3=el("td",{},[]);c3.appendChild(inp(a.abrege,7,function(v){a.abrege=v;}));
  var c4=el("td",{cls:"use"},[el("button",{cls:"d s",onclick:function(){
   D.apps.liste.splice(i,1);renderApps();}},["x"])]);
  tr.appendChild(c1);tr.appendChild(c2);tr.appendChild(c3);tr.appendChild(c4);
  tb.appendChild(tr);
 });
 var tr=el("tr",{cls:"sep"},[]);
 tr.appendChild(el("td",{},["tout le reste"]));
 var r1=el("td",{},[]);r1.appendChild(inp(D.apps.repli.profil,20,
  function(v){D.apps.repli.profil=v;}));
 var r2=el("td",{},[]);r2.appendChild(inp(D.apps.repli.abrege,7,
  function(v){D.apps.repli.abrege=v;}));
 tr.appendChild(r1);tr.appendChild(r2);tr.appendChild(el("td",{},[]));
 tb.appendChild(tr);
 z.appendChild(tb);
 z.appendChild(el("div",{cls:"bar2"},[el("button",{cls:"s",onclick:function(){
  D.apps.liste.push({exe:"",profil:D.ordre[0]||"",abrege:""});renderApps();}},
  ["+ Logiciel"])]));
}

function ren(anc,nv){nv=(nv||"").trim();if(!nv||D.profils[nv])return;
 D.profils[nv]=D.profils[anc];delete D.profils[anc];
 D.ordre=D.ordre.map(function(x){return x==anc?nv:x});render();}
function del(n){if(D.ordre.length<2)return say("Il faut au moins un profil",0);
 delete D.profils[n];D.ordre=D.ordre.filter(function(x){return x!=n});render();}
function addProfil(){var n="PROFIL",i=1;while(D.profils[n])n="PROFIL"+(++i);
 var t=[];for(var k=0;k<N;k++)t.push({label:"",usages:0});
 D.profils[n]={titre:n,couleur:"#808080",touches:t};
 D.ordre.push(n);render();}
function say(t,ok){var m=document.getElementById("msg");
 m.textContent=t;m.className=ok?"ok":"ko";m.style.display="block";
 window.scrollTo(0,document.body.scrollHeight);}
function dl(){var a=document.createElement("a");
 a.href=URL.createObjectURL(new Blob([JSON.stringify(D,null,2)],
  {type:"application/json"}));
 a.download="macropad_config.json";a.click();}
// =====================================================================
// RESTAURER UNE SAUVEGARDE
// =====================================================================
// Le bouton "Telecharger" existait depuis le debut, mais rien ne
// permettait de RECHARGER le fichier : la sauvegarde ne servait donc a
// rien. On charge le fichier dans le formulaire SANS l'appliquer, pour
// que tu voies ce que tu restaures avant de cliquer sur Enregistrer.
function charger_sauvegarde(texte){
 var d;
 try{d=JSON.parse(texte);}
 catch(e){say("Fichier illisible : "+e,0);return false;}
 if(!d||!d.ordre||!d.ordre.length||!d.profils){
  say("Ce fichier n'est pas une sauvegarde du macropad.",0);return false;}
 D=normaliser(d);N=d.touches||N;
 if(!D.apps)D.apps={repli:{profil:"WINDOWS",abrege:"Win"},liste:[]};
 render();
 say("Sauvegarde chargee : "+D.ordre.length+" profils. Verifie, puis "+
  "clique sur Enregistrer pour l'appliquer au macropad.",1);
 return true;}

function restaurer(){
 var i=el("input",{type:"file",accept:".json,application/json"});
 i.onchange=function(){
  var f=i.files&&i.files[0];if(!f)return;
  var lecteur=new FileReader();
  lecteur.onload=function(){charger_sauvegarde(lecteur.result);};
  lecteur.readAsText(f);};
 i.click();}

// Les compteurs d'usage vivent SUR LA CARTE : c'est elle qui compte les
// appuis. On lui demande donc de les oublier, puis on relit tout pour que
// les chiffres affiches soient bien ceux de la carte et non les notres.
function zero(){
 if(!confirm("Remettre a zero les compteurs d'usage des touches ?"))return;
 fetch("/api/compteurs",{method:"POST"}).then(function(r){return r.json();})
 .then(function(r){
  say(r.ok?"Compteurs remis a zero.":"Refuse :\n"+r.raison,r.ok);
  if(r.ok)charger();})
 .catch(function(e){say("Erreur : "+e,0);});}

function usine(){if(!confirm("Revenir aux valeurs d'usine ?"))return;
 fetch("/api/usine",{method:"POST"}).then(function(){location.reload();});}
function save(){fetch("/api/profils",{method:"POST",
 body:JSON.stringify(D)}).then(function(r){return r.json();})
 .then(function(r){say(r.ok?"Enregistre et applique.":"Refuse :\n"+r.raison,
  r.ok);if(r.ok)charger();})
 .catch(function(e){say("Erreur : "+e,0);});}
// Une sauvegarde ou un fichier ecrit avant les suites d'etapes range un
// SEUL objet par geste. On le remet en liste des la lecture : le reste de
// la page n'a ainsi qu'une seule forme a connaitre.
function normaliser(d){
 for(var nom in (d.profils||{})){
  ((d.profils[nom]||{}).touches||[]).forEach(function(k){
   GESTES.forEach(function(g){
    if(k[g]&&!(k[g] instanceof Array))k[g]=[k[g]];});});}
 return d;}

function charger(){fetch("/api/profils").then(function(r){return r.json();})
 .then(function(d){
  // La lecture a echoue. On affiche la raison ET la carte d'explication :
  // avant, on sortait ici, si bien que la seule chose visible etait une
  // ligne rouge sans la moindre piste - alors que vide() dit exactement
  // quoi verifier. Le conseil existait, il etait juste supprime pile au
  // moment ou il servait.
  if(d.erreur){
   say("Lecture impossible : "+d.erreur,0);
   document.getElementById("src").textContent="source : aucune";
   document.getElementById("cnt").textContent="macropad injoignable";
   D={ordre:[],profils:{},apps:{repli:{profil:"WINDOWS",abrege:"Win"},
    liste:[]}};
   render();
   return;}
  D=normaliser(d);N=d.touches||6;
  if(!D.apps)D.apps={repli:{profil:"WINDOWS",abrege:"Win"},liste:[]};
  document.getElementById("src").textContent="source : "+(d.origine||"?");
  var tot=0;for(var n in D.profils)(D.profils[n].touches||[]).forEach(
   function(t){tot+=t.usages||0;});
  document.getElementById("cnt").textContent=tot+" appuis comptes";
  render();}).catch(function(e){say("Erreur : "+e,0);});}
charger();
</script></body></html>
"""


def creer_serveur(macropad, table=None):
    class Handler(BaseHTTPRequestHandler):

        def log_message(self, *args):
            pass          # on ne veut pas polluer la console

        def _repondre(self, corps, mime="application/json", code=200):
            if isinstance(corps, str):
                corps = corps.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            if self.path.startswith("/api/profils"):
                try:
                    self._repondre(json.dumps(macropad.lire_config()))
                except Exception as exc:
                    self._repondre(json.dumps({"erreur": str(exc)}))
            else:
                self._repondre(PAGE, "text/html")

        def do_POST(self):
            if self.path.startswith("/api/compteurs"):
                try:
                    ok, raison = macropad.compteurs_a_zero()
                except Exception as exc:
                    ok, raison = False, str(exc)
                print("Compteurs :", "remis a zero" if ok
                      else "refuse (%s)" % raison)
                self._repondre(json.dumps({"ok": ok, "raison": raison}))
                return
            taille = int(self.headers.get("Content-Length", 0))
            corps = self.rfile.read(taille)
            try:
                data = json.loads(corps)
            except Exception as exc:
                self._repondre(json.dumps({"ok": False,
                                           "raison": "JSON invalide : %s" % exc}))
                return
            try:
                ok, raison = macropad.ecrire_config(data)
            except Exception as exc:
                ok, raison = False, str(exc)
            print("Configuration :", "appliquee" if ok else "refusee (%s)" % raison)
            if ok and table is not None:
                # La table des logiciels vient peut-etre d'etre modifiee :
                # on la relit tout de suite pour que la detection en tienne
                # compte des la seconde suivante.
                table.synchroniser(macropad)
            self._repondre(json.dumps({"ok": ok, "raison": raison}))

    return ThreadingHTTPServer(("127.0.0.1", PORT_WEB), Handler)


# =====================================================================
# 5. Programme principal
# =====================================================================
def main():
    analyseur = argparse.ArgumentParser(description="Compagnon du macropad")
    analyseur.add_argument("--port", help="port COM du macropad (sinon auto)")
    analyseur.add_argument("--simuler", action="store_true",
                           help="afficher ce qui serait envoye, sans macropad")
    analyseur.add_argument("--periode", type=float, default=0.4,
                           help="intervalle de detection en secondes")
    analyseur.add_argument("--journal", action="store_true",
                           help="ecrire aussi dans macropad_auto.log "
                                "(utilise par le demarrage automatique)")
    options = analyseur.parse_args()

    if options.journal:
        ouvrir_journal()

    if not options.simuler and not verifier_pyserial():
        return 1

    fenetre = FenetreActive()
    if not fenetre.disponible:
        print("ATTENTION : detection de la fenetre active indisponible")
        print("(ce script est prevu pour Windows). La page de configuration")
        print("fonctionne quand meme.")

    table = TableApplications(FICHIER_APPS)
    macropad = Macropad(options.port, options.simuler)
    table.synchroniser(macropad)        # la carte a le dernier mot

    serveur = creer_serveur(macropad, table)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    print("Page de configuration : http://127.0.0.1:%d" % PORT_WEB)
    print("Table des logiciels :", table.source)
    print("Ctrl-C pour arreter.")
    print("-" * 50)

    dernier_profil = None
    dernier_bas = None
    generation = macropad.generation
    prochaine_sync = time.time() + PERIODE_SYNC
    try:
        while True:
            maintenant = time.time()

            # Le macropad vient d'etre (re)branche : il a redemarre, il ne
            # sait plus quel profil afficher. On oublie ce qu'on croyait
            # lui avoir dit, et on relit sa table des logiciels.
            if macropad.generation != generation:
                generation = macropad.generation
                dernier_profil = dernier_bas = None
                prochaine_sync = maintenant

            if maintenant >= prochaine_sync:
                # On redemande la table a la carte : elle a pu changer
                # depuis le portail WiFi, sans que ce script le sache.
                # Si la carte se tait, on espace les tentatives pour ne pas
                # bloquer la detection toutes les 30 secondes.
                ok = table.synchroniser(macropad)
                prochaine_sync = maintenant + (PERIODE_SYNC if ok else 300.0)
            table.recharger()

            programme, titre = fenetre.lire()
            profil, abrege = table.regle(programme)
            document = nom_document(titre, programme)

            if profil != dernier_profil:
                print("%-22s -> %s" % (programme or "(inconnu)", profil))
                # On ne retient l'envoi comme fait que s'il est parti : si
                # le cable est debranche, il repartira a la reconnexion.
                if macropad.envoyer("P:" + profil):
                    dernier_profil = profil

            # L'ecran recoit "abrege|nom du fichier". L'abrege reste fixe en
            # bas a gauche, le nom defile a cote. On n'envoie que si quelque
            # chose a change : inutile de repeter la meme ligne 2 fois par
            # seconde.
            bas = "%s|%s" % (abrege, document)
            if bas != dernier_bas and macropad.envoyer("T:" + bas):
                dernier_bas = bas

            time.sleep(options.periode)
    except KeyboardInterrupt:
        print("\nArret.")
    finally:
        serveur.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
