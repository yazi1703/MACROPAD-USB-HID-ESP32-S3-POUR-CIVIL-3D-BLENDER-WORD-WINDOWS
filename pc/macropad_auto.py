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
        journee, il ne doit pas remplir la console de la meme phrase."""
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
                raise IOError("macropad non connecte")
            self.serie.reset_input_buffer()
            self._ecrire("?CFG")
            self._lire_reponse("#CFGBEGIN")
            morceaux = self._lire_reponse("#CFGEND")
        texte = "".join(m[3:] for m in morceaux if m.startswith("#C:"))
        return json.loads(texte)

    def ecrire_config(self, data):
        """Envoie une configuration. Retourne (True, "") ou (False, raison)."""
        texte = json.dumps(data)
        with self.verrou:
            if self.simuler:
                self._ecrire("!CFGBEGIN ... %d octets ... !CFGEND" % len(texte))
                return True, ""
            if not self.assurer():
                return False, "macropad non connecte"
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
<button class=d onclick=usine()>Valeurs d'usine</button>
</div>
<div id=msg></div>
</main>
<script>
var D={ordre:[],profils:{},apps:{repli:{profil:"WINDOWS",abrege:"Win"},liste:[]}};
var N=6,GESTES=["court","long","double"];
var LIB={court:"court",long:"long",double:"double"};
var TYPES=[["none","inactive"],["key","touche"],["combo","combinaison"],
["text","texte"],["text_enter","texte + Entree"]];

function el(tag,attrs,kids){var e=document.createElement(tag);
 for(var k in attrs||{}){if(k=="cls")e.className=attrs[k];
  else if(k.slice(0,2)=="on")e[k]=attrs[k];else e.setAttribute(k,attrs[k]);}
 (kids||[]).forEach(function(c){
  e.appendChild(typeof c=="string"?document.createTextNode(c):c);});
 return e;}
function inp(val,max,cb){var i=el("input");i.value=val||"";
 if(max)i.maxLength=max;i.oninput=function(){cb(i.value);};return i;}
function sel(val,cb){var s=el("select");TYPES.forEach(function(t){
 var o=el("option",{value:t[0]},[t[1]]);if(t[0]==val)o.selected=true;
 s.appendChild(o);});s.onchange=function(){cb(s.value);render();};return s;}

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
  c.appendChild(el("p",{},["Verifie qu'il est branche sur son port USB "+
   "NATIF, et que Thonny n'occupe pas ce port."]));
  c.appendChild(el("p",{},["La console du compagnon dit ce qu'elle voit ; "+
   "avec --journal, tout est dans macropad_auto.log."]));
 }
 c.appendChild(el("p",{},["Tu peux aussi partir des valeurs d'usine avec le "+
  "bouton rouge, ou ajouter un profil ci-dessous."]));
 return c;}

function render(){
 var zone=document.getElementById("profs");zone.innerHTML="";
 var mx=maxUse();
 if(!D.ordre.length){zone.appendChild(vide());renderApps();return;}
 D.ordre.forEach(function(nom){
  var p=D.profils[nom];if(!p)return;
  var head=el("div",{cls:"ph"},[]);
  head.appendChild(inp(nom,20,function(v){ren(nom,v);}));
  head.firstChild.className="grow";head.firstChild.title="nom interne";
  var t=inp(p.titre,16,function(v){p.titre=v;});t.className="grow";
  t.title="titre affiche sur l'ecran";head.appendChild(t);
  head.appendChild(el("button",{cls:"d s",onclick:function(){del(nom);}},
   ["Supprimer"]));
  var tb=el("table",{},[el("tr",{},[el("th",{},["#"]),el("th",{},["Geste"]),
   el("th",{},["Libelle"]),el("th",{},["Type"]),el("th",{},["Valeur"]),
   el("th",{},["Usage"])])]);
  for(var i=0;i<N;i++){
   if(!p.touches[i])p.touches[i]={label:"",usages:0};
   var k=p.touches[i];
   GESTES.forEach(function(g,gi){
    if(!k[g])k[g]={type:"none",valeur:""};
    var tr=el("tr",{cls:gi==0?"sep":""},[]);
    if(gi==0){var c=el("td",{cls:"k",rowspan:3},["B"+(i+1)]);tr.appendChild(c);}
    tr.appendChild(el("td",{cls:"g"},[LIB[g]]));
    if(gi==0){
     var cl=el("td",{cls:"lab",rowspan:3},[]);
     cl.appendChild(inp(k.label,6,function(v){k.label=v;}));
     tr.appendChild(cl);
    }
    var ct=el("td",{cls:"ty"},[]);
    ct.appendChild(sel(k[g].type,function(v){k[g].type=v;}));
    tr.appendChild(ct);
    var cv=el("td",{},[]);
    cv.appendChild(inp(k[g].valeur,60,function(v){k[g].valeur=v;}));
    tr.appendChild(cv);
    if(gi==0){
     var u=k.usages||0;
     var box=el("td",{cls:"use",rowspan:3},[String(u)]);
     var b=el("div",{cls:"bar"});b.style.width=Math.round(60*u/mx)+"px";
     box.appendChild(b);tr.appendChild(box);
    }
    tb.appendChild(tr);
   });
  }
  zone.appendChild(el("div",{cls:"card"},[head,tb]));
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
 D.profils[n]={titre:n,touches:t};D.ordre.push(n);render();}
function say(t,ok){var m=document.getElementById("msg");
 m.textContent=t;m.className=ok?"ok":"ko";m.style.display="block";
 window.scrollTo(0,document.body.scrollHeight);}
function dl(){var a=document.createElement("a");
 a.href=URL.createObjectURL(new Blob([JSON.stringify(D,null,2)],
  {type:"application/json"}));
 a.download="macropad_config.json";a.click();}
function usine(){if(!confirm("Revenir aux valeurs d'usine ?"))return;
 fetch("/api/usine",{method:"POST"}).then(function(){location.reload();});}
function save(){fetch("/api/profils",{method:"POST",
 body:JSON.stringify(D)}).then(function(r){return r.json();})
 .then(function(r){say(r.ok?"Enregistre et applique.":"Refuse :\n"+r.raison,
  r.ok);if(r.ok)charger();})
 .catch(function(e){say("Erreur : "+e,0);});}
function charger(){fetch("/api/profils").then(function(r){return r.json();})
 .then(function(d){
  if(d.erreur)return say("Lecture impossible : "+d.erreur,0);
  D=d;N=d.touches||6;if(!D.apps)D.apps={repli:{profil:"WINDOWS",abrege:"Win"},
   liste:[]};
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
