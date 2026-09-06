# -*- coding: utf-8 -*-
"""
demarrage_windows.py - Lancer le compagnon du macropad a l'ouverture de session.

=====================================================================
A QUOI CA SERT
=====================================================================
Sans ca, il faut penser a lancer macropad_auto.py a chaque demarrage du
PC. Ce script installe (ou retire) un raccourci dans le dossier de
demarrage de Windows, celui que tu ouvrirais toi-meme avec

    Win+R  puis  shell:startup

Le raccourci lance macropad_auto.bat en fenetre REDUITE, avec l'option
--journal : tout ce que le script raconte est ecrit dans
macropad_auto.log, a cote de lui. C'est la qu'il faut regarder si un jour
la detection ne marche pas.

=====================================================================
UTILISATION
=====================================================================
Double-clique sur demarrage_windows.bat, ou :

    py demarrage_windows.py                 menu
    py demarrage_windows.py --installer
    py demarrage_windows.py --desinstaller
    py demarrage_windows.py --etat

=====================================================================
CE QUE CA NE FAIT PAS
=====================================================================
* Aucun service Windows, aucune tache planifiee, rien dans la base de
  registre : juste un fichier .lnk dans TON dossier de demarrage. Tu peux
  le supprimer a la main, ca revient exactement au meme.
* Aucun droit administrateur n'est demande, et il n'en faut pas.
* Le macropad tape uniquement ce que tu lui as demande : ce raccourci ne
  change rien a ce qu'il envoie, il lance seulement le compagnon.
"""

import argparse
import os
import subprocess
import sys

DOSSIER = os.path.dirname(os.path.abspath(__file__))
CIBLE = os.path.join(DOSSIER, "macropad_auto.bat")
NOM_RACCOURCI = "Macropad.lnk"
ARGUMENTS = "--journal"
DESCRIPTION = "Compagnon du macropad : profil suivant le logiciel actif"
REDUITE = 7          # WindowStyle : 1 = normale, 3 = maximisee, 7 = reduite


# =====================================================================
# Ou Windows range les programmes a lancer a l'ouverture de session
# =====================================================================
def dossier_demarrage(environnement=None):
    """Le dossier « shell:startup » de l'utilisateur courant."""
    env = environnement if environnement is not None else os.environ
    base = env.get("APPDATA")
    if not base:
        raise RuntimeError(
            "APPDATA introuvable : ce script est prevu pour Windows.")
    return os.path.join(base, "Microsoft", "Windows", "Start Menu",
                        "Programs", "Startup")


def chemin_raccourci(environnement=None):
    return os.path.join(dossier_demarrage(environnement), NOM_RACCOURCI)


# =====================================================================
# Fabrication du raccourci
# =====================================================================
def _texte_ps(valeur):
    """Met une valeur entre apostrophes pour PowerShell.

    Dans une chaine PowerShell entre apostrophes, rien n'est interprete —
    ni les antislash des chemins Windows, ni le $ — sauf l'apostrophe
    elle-meme, qu'on double. C'est la forme la plus sure pour des chemins.
    """
    return "'" + str(valeur).replace("'", "''") + "'"


def commande_powershell(raccourci, cible=CIBLE, arguments=ARGUMENTS,
                        dossier=DOSSIER, style=REDUITE):
    """Le script PowerShell qui cree le .lnk. Sorti a part pour etre testable."""
    return (
        "$r = (New-Object -ComObject WScript.Shell).CreateShortcut(%s); "
        "$r.TargetPath = %s; "
        "$r.Arguments = %s; "
        "$r.WorkingDirectory = %s; "
        "$r.WindowStyle = %d; "
        "$r.Description = %s; "
        "$r.Save()"
        % (_texte_ps(raccourci), _texte_ps(cible), _texte_ps(arguments),
           _texte_ps(dossier), int(style), _texte_ps(DESCRIPTION)))


def installer():
    """Cree le raccourci. Retourne True si tout s'est bien passe."""
    if not os.path.exists(CIBLE):
        print("Introuvable :", CIBLE)
        print("Ce script doit rester dans le dossier pc/ du projet.")
        return False

    raccourci = chemin_raccourci()
    dossier = os.path.dirname(raccourci)
    if not os.path.isdir(dossier):
        print("Dossier de demarrage introuvable :", dossier)
        return False

    resultat = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-Command", commande_powershell(raccourci)],
        capture_output=True, text=True)
    if resultat.returncode != 0 or not os.path.exists(raccourci):
        print("La creation du raccourci a echoue.")
        if resultat.stderr.strip():
            print(resultat.stderr.strip())
        return False

    print("Installe :", raccourci)
    print("  -> lance :", CIBLE, ARGUMENTS)
    print("  -> en fenetre reduite, a chaque ouverture de session.")
    print()
    print("Le compagnon demarrera au prochain demarrage de Windows.")
    print("Pour l'utiliser tout de suite, double-clique sur macropad_auto.bat.")
    _verifier_pyserial()
    return True


def desinstaller():
    """Retire le raccourci. Ne se plaint pas s'il n'y est plus."""
    raccourci = chemin_raccourci()
    if not os.path.exists(raccourci):
        print("Rien a retirer : aucun raccourci dans le dossier de demarrage.")
        return True
    try:
        os.remove(raccourci)
    except OSError as exc:
        print("Suppression impossible (%s)." % exc)
        return False
    print("Retire :", raccourci)
    print("Le compagnon ne demarrera plus tout seul.")
    return True


def etat():
    """Dit si le raccourci est en place."""
    raccourci = chemin_raccourci()
    if os.path.exists(raccourci):
        print("Demarrage automatique : ACTIF")
        print("  ", raccourci)
    else:
        print("Demarrage automatique : inactif")
        print("   (aucun raccourci dans %s)" % dossier_demarrage())
    journal = os.path.join(DOSSIER, "macropad_auto.log")
    if os.path.exists(journal):
        print("Journal :", journal, "(%d octets)" % os.path.getsize(journal))
    return True


def _verifier_pyserial():
    """Un raccourci qui lance un script sans pyserial ne sert a rien."""
    try:
        import serial               # noqa: F401
    except ImportError:
        print()
        print("ATTENTION : pyserial n'est pas installe pour CE Python.")
        print("            Lance :  py -m pip install pyserial")


# =====================================================================
# Programme principal
# =====================================================================
def menu():
    print("Demarrage automatique du compagnon du macropad")
    print("-" * 46)
    etat()
    print()
    print("  1. Installer   (lancer au demarrage de Windows)")
    print("  2. Desinstaller")
    print("  3. Ne rien faire")
    try:
        choix = input("Ton choix [1/2/3] : ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return True
    print()
    if choix == "1":
        return installer()
    if choix == "2":
        return desinstaller()
    print("Rien n'a ete modifie.")
    return True


def main(argv=None):
    analyseur = argparse.ArgumentParser(
        description="Lancer le compagnon du macropad au demarrage de Windows")
    groupe = analyseur.add_mutually_exclusive_group()
    groupe.add_argument("--installer", action="store_true")
    groupe.add_argument("--desinstaller", action="store_true")
    groupe.add_argument("--etat", action="store_true")
    options = analyseur.parse_args(argv)

    if sys.platform != "win32":
        print("Ce script ne sert que sous Windows.")
        print("Sur un autre systeme, lance macropad_auto.py a la main.")
        return 1

    if options.installer:
        ok = installer()
    elif options.desinstaller:
        ok = desinstaller()
    elif options.etat:
        ok = etat()
    else:
        ok = menu()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
