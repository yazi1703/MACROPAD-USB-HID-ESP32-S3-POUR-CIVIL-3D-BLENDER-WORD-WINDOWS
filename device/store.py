# -*- coding: utf-8 -*-
"""
store.py - Enregistrement des profils personnalisés sur la carte.

=====================================================================
À QUOI ÇA SERT
=====================================================================
La page web du mode configuration modifie tes profils. Il faut bien les
ranger quelque part pour qu'ils survivent au débranchement : c'est le rôle
de ce module. Il lit et écrit un fichier JSON sur la mémoire flash de la
carte (`profils.json` par défaut).

Le JSON est un format texte simple, lisible, que tu peux ouvrir dans
Thonny pour voir ce que contient ta configuration.

=====================================================================
DEUX RÈGLES DE SÉCURITÉ
=====================================================================
1. **Rien n'est enregistré sans avoir été vérifié.** Chaque macro est
   traduite en codes clavier AVANT l'écriture. Si un caractère est
   impossible à taper ou si un nom de touche est inconnu, l'enregistrement
   est refusé avec un message clair. Impossible d'enregistrer une
   configuration qui planterait au prochain démarrage.

2. **Le fichier n'est jamais indispensable.** S'il est absent, illisible
   ou incohérent, le firmware repart sur les profils d'usine de
   `profiles.py` en le signalant dans le REPL. Une carte ne peut pas
   devenir inutilisable à cause de ce fichier ; au pire, efface-le.

=====================================================================
FORME DU FICHIER
=====================================================================
    {
      "version": 1,
      "ordre": ["BLENDER", "CIVIL3D", "WORD", "WINDOWS"],
      "profils": {
        "CIVIL3D": {
          "titre": "CIVIL 3D",
          "touches": [
            {"label": "MATCH", "type": "text_enter", "valeur": "_MATCHPROP"},
            ...
          ]
        }
      }
    }

Le "type" vaut "key", "combo", "text", "text_enter" ou "none".
Pour un "combo", la valeur s'écrit avec des plus : "CTRL+SHIFT+ESC".
"""

import json
import config as C
import profiles as P
from layouts import compile_actions

TYPES = ("key", "combo", "text", "text_enter", "none")


# =====================================================================
# Conversion entre la forme JSON (page web) et la forme interne (firmware)
# =====================================================================
def action_vers_json(actions):
    """Forme interne -> (type, valeur texte) pour la page web."""
    if not actions:
        return "none", ""
    kind, value = actions[0]
    if kind == "combo":
        return "combo", "+".join(value)
    return kind, str(value)


def action_depuis_json(kind, valeur):
    """(type, valeur texte) -> forme interne."""
    if kind == "none":
        return []
    if kind == "combo":
        touches = tuple(p.strip() for p in str(valeur).split("+") if p.strip())
        if not touches:
            raise ValueError("combinaison vide")
        return [("combo", touches)]
    if kind in ("key", "text", "text_enter"):
        return [(kind, str(valeur))]
    raise ValueError("type inconnu : " + str(kind))


# =====================================================================
# Vérification
# =====================================================================
def verifier(profils, ordre, nb_touches):
    """Retourne la liste des problèmes. Liste vide = configuration saine."""
    problemes = []

    if not ordre:
        problemes.append("l'ordre des profils est vide")
    if len(set(ordre)) != len(ordre):
        problemes.append("un profil apparait deux fois dans l'ordre")

    for nom in ordre:
        if nom not in profils:
            problemes.append("l'ordre cite '%s' qui n'existe pas" % nom)

    for nom, macros in profils.items():
        if len(macros) != nb_touches:
            problemes.append("%s : %d touches au lieu de %d"
                             % (nom, len(macros), nb_touches))
        for index, macro in enumerate(macros):
            label, actions = macro
            if len(label) > P.LABEL_MAX:
                problemes.append("%s B%d : libelle '%s' depasse %d caracteres"
                                 % (nom, index + 1, label, P.LABEL_MAX))
            try:
                # La vérification qui compte : la macro est-elle réellement
                # tapable avec la disposition clavier choisie ?
                compile_actions(actions, C.KEYBOARD_LAYOUT)
            except Exception as exc:
                problemes.append("%s B%d (%s) : %s"
                                 % (nom, index + 1, label, exc))
    return problemes


# =====================================================================
# Lecture
# =====================================================================
def defauts():
    """Copie des profils d'usine, dans la forme interne."""
    profils = {}
    for nom, macros in P.PROFILES.items():
        profils[nom] = [(label, list(actions)) for label, actions in macros]
    return profils, list(C.PROFILES_ORDER)


def charger(nb_touches):
    """Retourne (profils, ordre, titres, origine).

    origine vaut "fichier" ou "usine" : main.py s'en sert pour te dire
    d'où viennent les macros actives.
    """
    titres = dict(P.TITLES)
    try:
        with open(C.PROFILES_FILE) as fichier:
            data = json.load(fichier)
    except OSError:
        return defauts() + (titres, "usine")          # fichier absent : normal
    except Exception as exc:
        print("[store] %s illisible (%s), retour aux profils d'usine"
              % (C.PROFILES_FILE, exc))
        return defauts() + (titres, "usine")

    try:
        ordre = [str(n) for n in data["ordre"]]
        profils = {}
        for nom, bloc in data["profils"].items():
            macros = []
            for touche in bloc["touches"]:
                actions = action_depuis_json(touche.get("type", "none"),
                                             touche.get("valeur", ""))
                macros.append((str(touche.get("label", ""))[:P.LABEL_MAX],
                               actions))
            profils[str(nom)] = macros
            if bloc.get("titre"):
                titres[str(nom)] = str(bloc["titre"])
    except Exception as exc:
        print("[store] %s mal formé (%s), retour aux profils d'usine"
              % (C.PROFILES_FILE, exc))
        return defauts() + (dict(P.TITLES), "usine")

    problemes = verifier(profils, ordre, nb_touches)
    if problemes:
        print("[store] %s refuse, retour aux profils d'usine :" % C.PROFILES_FILE)
        for probleme in problemes:
            print("   -", probleme)
        return defauts() + (dict(P.TITLES), "usine")

    return profils, ordre, titres, "fichier"


# =====================================================================
# Écriture
# =====================================================================
def enregistrer(profils, ordre, titres, nb_touches):
    """Vérifie puis écrit le fichier. Retourne (True, "") ou (False, raison)."""
    problemes = verifier(profils, ordre, nb_touches)
    if problemes:
        return False, " ; ".join(problemes)

    blocs = {}
    for nom, macros in profils.items():
        touches = []
        for label, actions in macros:
            kind, valeur = action_vers_json(actions)
            touches.append({"label": label, "type": kind, "valeur": valeur})
        blocs[nom] = {"titre": titres.get(nom, nom), "touches": touches}

    data = {"version": 1, "ordre": list(ordre), "profils": blocs}
    try:
        # On écrit d'abord un fichier temporaire, puis on le renomme :
        # une coupure de courant en plein enregistrement ne peut donc pas
        # laisser un profils.json à moitié écrit.
        temporaire = C.PROFILES_FILE + ".tmp"
        with open(temporaire, "w") as fichier:
            json.dump(data, fichier)
        try:
            import os
            os.remove(C.PROFILES_FILE)
        except OSError:
            pass
        import os
        os.rename(temporaire, C.PROFILES_FILE)
    except Exception as exc:
        return False, "ecriture impossible : %s" % exc
    return True, ""


def effacer():
    """Supprime le fichier : retour aux profils d'usine au prochain RESET."""
    try:
        import os
        os.remove(C.PROFILES_FILE)
        return True
    except OSError:
        return False
