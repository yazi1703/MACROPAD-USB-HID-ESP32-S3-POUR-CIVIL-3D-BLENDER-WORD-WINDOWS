#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verifier_agenda.py - Dit ce que le compagnon comprend de ton fichier.

=====================================================================
A QUOI CA SERT
=====================================================================
Quand l'agenda vient d'un flux Power Automate, personne ne voit ce qui
sort. Si trois reunions sur cinq manquent a l'ecran, la question est
"pourquoi ?" - et sans reponse, on cherche au mauvais endroit.

Cet outil repond. Il lit le fichier avec LE MEME CODE que le compagnon,
et il dit, pour chaque entree : gardee, ou ecartee et pour quelle raison.

    python3 tools/verifier_agenda.py mon_agenda.json
    python3 tools/verifier_agenda.py mon_agenda.json 2026-09-14

=====================================================================
CE QU'IL ATTRAPE, ET QUE RIEN D'AUTRE N'ATTRAPE
=====================================================================
LE FUSEAU HORAIRE. Un calendrier d'entreprise donne souvent ses heures
en UTC. Rien ne le signale : les reunions s'affichent, simplement
decalees d'une ou deux heures selon la saison. On arrive en retard en
croyant etre en avance.

L'outil montre donc, pour chaque evenement, L'HEURE BRUTE DU FICHIER a
cote de l'heure convertie. Un coup d'oeil a Teams, et le doute est leve.
"""

import datetime
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "pc"))

import macropad_auto as MA                                   # noqa: E402


def _brut(entree):
    """L'heure de debut telle qu'elle est ECRITE dans le fichier."""
    valeur = MA._texte_datetime(MA._champ(entree, MA._CHAMPS_DEBUT))
    return str(valeur or "?")


def _resume_entree(entree):
    """De quoi reconnaitre une entree ecartee, sans vomir tout le JSON."""
    if not isinstance(entree, dict):
        return repr(entree)[:60]
    titre = MA._champ(entree, MA._CHAMPS_TITRE) or "(sans titre)"
    return "%s  [%s]" % (str(titre)[:40], _brut(entree))


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip().split("\n\n")[2])
        return 2
    chemin = sys.argv[1]
    if len(sys.argv) > 2:
        aujourdhui = datetime.date.fromisoformat(sys.argv[2])
    else:
        aujourdhui = datetime.date.today()

    try:
        with open(chemin, encoding="utf-8") as fichier:
            donnees = json.load(fichier)
    except OSError as exc:
        print("Fichier illisible : %s" % exc)
        return 1
    except ValueError as exc:
        print("Ce n'est pas du JSON valable : %s" % exc)
        print("\nUn flux Power Automate qui ecrit du texte brut, ou un")
        print("fichier a moitie ecrit au moment de la lecture, donnent ca.")
        return 1

    decalage = datetime.datetime.now().astimezone().utcoffset()
    print("Fichier     : %s" % chemin)
    print("Journee     : %s" % aujourdhui)
    print("Fuseau du PC: UTC%+03d:%02d"
          % (decalage.total_seconds() // 3600,
             abs(decalage.total_seconds()) % 3600 // 60))
    print()

    gardes, rejets = MA.examiner_agenda(donnees, aujourdhui)
    brut = donnees.get("evenements") if isinstance(donnees, dict) else donnees
    if isinstance(donnees, dict) and brut is None:
        brut = donnees.get("value")
    print("%d entree(s) lue(s), %d gardee(s), %d ecartee(s)."
          % (len(brut or []), len(gardes), len(rejets)))

    if gardes:
        print("\nGARDEES")
        for debut, fin, titre in gardes:
            print("  %02d:%02d - %02d:%02d   %s"
                  % (debut // 60, debut % 60, fin // 60, fin % 60, titre))

    if rejets:
        print("\nECARTEES")
        for entree, raison in rejets:
            print("  %-52s %s" % (_resume_entree(entree), raison))

    # LE FUSEAU QU'ON NE SAIT PAS TRADUIRE. On ne devine jamais - un
    # fuseau invente serait la panne silencieuse qu'on cherche a eviter -
    # mais se taire serait aussi grave : l'agenda s'afficherait, decale.
    inconnus = set()
    for entree in (brut or []):
        if not isinstance(entree, dict):
            continue
        noms = [str(entree.get("timeZone", entree.get("timezone", "")) or "")]
        for cle in MA._CHAMPS_DEBUT + MA._CHAMPS_FIN:
            noms.append(MA._zone_declaree(entree.get(cle)))
        for nom in noms:
            if nom and MA._fuseau(nom) is None:
                inconnus.add(nom)
    if inconnus:
        print("\n" + "!" * 66)
        print("FUSEAU NON TRADUIT : %s" % ", ".join(sorted(inconnus)))
        print("Ces heures sont prises TELLES QUELLES, sans conversion.")
        print("Si elles ne correspondent pas a Teams, regle ton flux pour")
        print("qu'il sorte les heures en UTC - c'est le reglage par defaut")
        print("de Microsoft Graph, et le seul qu'on traduise a coup sur.")
        print("!" * 66)

    lignes = MA.lignes_agenda(gardes)
    print("\nCE QUI PARTIRAIT VERS LA CARTE")
    for ligne in lignes:
        print("  %s" % ligne)

    # Le controle que l'outil existe pour rendre possible.
    if gardes and isinstance(brut, list):
        print("\n" + "=" * 66)
        print("VERIFIE CES HEURES CONTRE CE QUE TU VOIS DANS TEAMS.")
        print("Un decalage CONSTANT de 1 ou 2 heures sur tout l'agenda est")
        print("un probleme de fuseau, pas un probleme de macropad :")
        for entree in brut[:3]:
            if isinstance(entree, dict):
                converti = MA.instant(
                    MA._champ(entree, MA._CHAMPS_DEBUT), aujourdhui,
                    str(entree.get("timeZone",
                                   entree.get("timezone", "")) or ""))
                if converti is not None:
                    print("   fichier %-26s ->  affiche %02d:%02d"
                          % (_brut(entree), converti.hour, converti.minute))
        print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
