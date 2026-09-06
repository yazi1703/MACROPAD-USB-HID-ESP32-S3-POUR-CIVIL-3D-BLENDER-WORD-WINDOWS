# -*- coding: utf-8 -*-
"""
store.py - Enregistrement de la configuration sur la carte.

=====================================================================
A QUOI CA SERT
=====================================================================
Les pages web modifient tes profils, tes macros et ta liste de logiciels.
Il faut bien ranger tout cela quelque part pour que ca survive au
debranchement : c'est le role de ce module. Il lit et ecrit un fichier
JSON sur la memoire flash (`profils.json` par defaut).

Le JSON est un format texte simple, lisible, que tu peux ouvrir dans
Thonny pour voir ce que contient ta configuration.

C'est aussi ici qu'est definie la forme d'echange avec les deux pages web
(vers_json / depuis_json) : le portail WiFi et le compagnon USB parlent
donc exactement le meme langage.

=====================================================================
DEUX REGLES DE SECURITE
=====================================================================
1. **Rien n'est enregistre sans avoir ete verifie.** Chaque macro est
   traduite en codes clavier AVANT l'ecriture. Si un caractere est
   impossible a taper ou si un nom de touche est inconnu, l'enregistrement
   est refuse avec un message clair. Impossible d'enregistrer une
   configuration qui planterait au prochain demarrage.

2. **Le fichier n'est jamais indispensable.** S'il est absent, illisible
   ou incoherent, le firmware repart sur les valeurs d'usine de
   profiles.py en le signalant dans le REPL. Une carte ne peut pas
   devenir inutilisable a cause de ce fichier ; au pire, efface-le.

=====================================================================
FORME DU FICHIER
=====================================================================
    {
      "version": 2,
      "ordre": ["BLENDER", "CIVIL3D", "WORD", "WINDOWS"],
      "profils": {
        "CIVIL3D": {
          "titre": "CIVIL 3D",
          "touches": [
            {"label": "MATCH",
             "court":  {"type": "text_enter", "valeur": "_MATCHPROP"},
             "long":   {"type": "none", "valeur": ""},
             "double": {"type": "none", "valeur": ""}},
            ...
          ]
        }
      },
      "apps": {
        "repli": {"profil": "WINDOWS", "abrege": "Win"},
        "liste": [{"exe": "acad.exe", "profil": "CIVIL3D", "abrege": "C3D"}]
      }
    }

Le "type" vaut "key", "combo", "text", "text_enter" ou "none".
Pour un "combo", la valeur s'ecrit avec des plus : "CTRL+SHIFT+ESC".
"""

import json
import config as C
import profiles as P
from layouts import compile_actions

TYPES = ("key", "combo", "text", "text_enter", "none")


# =====================================================================
# Conversion entre la forme des pages web et la forme interne
# =====================================================================
def action_vers_json(actions):
    """Forme interne -> (type, valeur texte) pour les formulaires."""
    if not actions:
        return "none", ""
    genre, valeur = actions[0]
    if genre == "combo":
        return "combo", "+".join(valeur)
    return genre, str(valeur)


def action_depuis_json(genre, valeur):
    """(type, valeur texte) -> forme interne."""
    if genre == "none" or (genre in ("text", "text_enter") and not valeur):
        return []
    if genre == "combo":
        touches = tuple(p.strip() for p in str(valeur).split("+") if p.strip())
        if not touches:
            raise ValueError("combinaison vide")
        return [("combo", touches)]
    if genre in ("key", "text", "text_enter"):
        if not str(valeur).strip():
            return []
        return [(genre, str(valeur))]
    raise ValueError("type inconnu : " + str(genre))


# =====================================================================
# Verification
# =====================================================================
def verifier(profils, ordre, nb_touches):
    """Retourne la liste des problemes. Liste vide = configuration saine."""
    problemes = []

    if not ordre:
        problemes.append("l'ordre des profils est vide")
    if len(set(ordre)) != len(ordre):
        problemes.append("un profil apparait deux fois dans l'ordre")
    for nom in ordre:
        if nom not in profils:
            problemes.append("l'ordre cite '%s' qui n'existe pas" % nom)

    for nom, touches in profils.items():
        if len(touches) != nb_touches:
            problemes.append("%s : %d touches au lieu de %d"
                             % (nom, len(touches), nb_touches))
        for index, (label, gestes) in enumerate(touches):
            if len(label) > P.LABEL_MAX:
                problemes.append("%s B%d : libelle '%s' depasse %d caracteres"
                                 % (nom, index + 1, label, P.LABEL_MAX))
            if not (gestes or {}).get(P.COURT):
                # Un appui court vide est autorise : la touche est inactive.
                pass
            for geste, actions in (gestes or {}).items():
                if geste not in P.GESTES:
                    problemes.append("%s B%d : geste inconnu '%s'"
                                     % (nom, index + 1, geste))
                    continue
                try:
                    # La verification qui compte : la macro est-elle
                    # reellement tapable avec la disposition choisie ?
                    compile_actions(actions, C.KEYBOARD_LAYOUT)
                except Exception as exc:
                    problemes.append("%s B%d %s (%s) : %s"
                                     % (nom, index + 1, geste, label, exc))
    return problemes


# =====================================================================
# Valeurs d'usine
# =====================================================================
def defauts():
    """Copie des valeurs d'usine, dans la forme interne."""
    profils = {}
    for nom, touches in P.PROFILES.items():
        profils[nom] = [(label, dict(gestes)) for label, gestes in touches]
    apps = [tuple(a) for a in P.APPS]
    return profils, list(C.PROFILES_ORDER), dict(P.TITLES), apps, tuple(P.APPS_REPLI)


# =====================================================================
# Conversion vers et depuis les pages web
# =====================================================================
def vers_json(nb_touches, stats=None):
    """Configuration complete, prete a etre envoyee a une page web."""
    profils, ordre, titres, apps, repli, origine = charger(nb_touches)
    blocs = {}
    for nom, touches in profils.items():
        liste = []
        for index, (label, gestes) in enumerate(touches):
            entree = {"label": label}
            for geste in P.GESTES:
                genre, valeur = action_vers_json((gestes or {}).get(geste))
                entree[geste] = {"type": genre, "valeur": valeur}
            if stats is not None:
                entree["usages"] = stats.pour(nom)[index]
            liste.append(entree)
        blocs[nom] = {"titre": titres.get(nom, nom), "touches": liste}

    return {
        "version": 2,
        "ordre": ordre,
        "profils": blocs,
        "apps": {
            "repli": {"profil": repli[0], "abrege": repli[1]},
            "liste": [{"exe": e, "profil": p, "abrege": a} for e, p, a in apps],
        },
        "touches": nb_touches,
        "gestes": list(P.GESTES),
        "origine": origine,
    }


def depuis_json(data, nb_touches):
    """Forme web -> forme interne. Leve une exception si c'est illisible."""
    ordre = [str(n) for n in data["ordre"]]
    profils, titres = {}, {}
    for nom, bloc in data["profils"].items():
        touches = []
        for entree in bloc["touches"][:nb_touches]:
            gestes = {}
            if "type" in entree and not any(g in entree for g in P.GESTES):
                # Fichier de version 1 : une seule macro par touche, ecrite
                # a plat. On la reprend comme appui court, les deux autres
                # gestes restent libres. Personne ne perd sa configuration
                # en mettant le firmware a jour.
                entree = dict(entree)
                entree[P.COURT] = {"type": entree.get("type", "none"),
                                   "valeur": entree.get("valeur", "")}
            for geste in P.GESTES:
                champ = entree.get(geste) or {}
                actions = action_depuis_json(champ.get("type", "none"),
                                             champ.get("valeur", ""))
                if actions:
                    gestes[geste] = actions
            touches.append((str(entree.get("label", ""))[:P.LABEL_MAX], gestes))
        while len(touches) < nb_touches:
            touches.append(("", {}))
        profils[str(nom)] = touches
        titres[str(nom)] = str(bloc.get("titre", nom))

    bloc_apps = data.get("apps") or {}
    apps = []
    for entree in bloc_apps.get("liste", []):
        exe = str(entree.get("exe", "")).strip().lower()
        if exe:
            apps.append((exe, str(entree.get("profil", "")).strip().upper(),
                         str(entree.get("abrege", ""))[:7]))
    bloc_repli = bloc_apps.get("repli") or {}
    repli = (str(bloc_repli.get("profil", P.APPS_REPLI[0])).upper(),
             str(bloc_repli.get("abrege", P.APPS_REPLI[1]))[:7])
    return profils, ordre, titres, apps, repli


# =====================================================================
# Lecture et ecriture du fichier
# =====================================================================
def charger(nb_touches):
    """Retourne (profils, ordre, titres, apps, repli, origine).

    origine vaut "fichier" ou "usine" : main.py s'en sert pour te dire d'ou
    viennent les macros actives.
    """
    try:
        with open(C.PROFILES_FILE) as fichier:
            data = json.load(fichier)
    except OSError:
        return defauts() + ("usine",)              # fichier absent : normal
    except Exception as exc:
        print("[store] %s illisible (%s), retour aux valeurs d'usine"
              % (C.PROFILES_FILE, exc))
        return defauts() + ("usine",)

    try:
        profils, ordre, titres, apps, repli = depuis_json(data, nb_touches)
    except Exception as exc:
        print("[store] %s mal forme (%s), retour aux valeurs d'usine"
              % (C.PROFILES_FILE, exc))
        return defauts() + ("usine",)

    problemes = verifier(profils, ordre, nb_touches)
    if problemes:
        print("[store] %s refuse, retour aux valeurs d'usine :" % C.PROFILES_FILE)
        for probleme in problemes:
            print("   -", probleme)
        return defauts() + ("usine",)

    return profils, ordre, titres, apps, repli, "fichier"


def enregistrer(profils, ordre, titres, apps, repli, nb_touches):
    """Verifie puis ecrit. Retourne (True, "") ou (False, raison)."""
    problemes = verifier(profils, ordre, nb_touches)
    if problemes:
        return False, " ; ".join(problemes)

    blocs = {}
    for nom, touches in profils.items():
        liste = []
        for label, gestes in touches:
            entree = {"label": label}
            for geste in P.GESTES:
                genre, valeur = action_vers_json((gestes or {}).get(geste))
                entree[geste] = {"type": genre, "valeur": valeur}
            liste.append(entree)
        blocs[nom] = {"titre": titres.get(nom, nom), "touches": liste}

    data = {"version": 2, "ordre": list(ordre), "profils": blocs,
            "apps": {"repli": {"profil": repli[0], "abrege": repli[1]},
                     "liste": [{"exe": e, "profil": p, "abrege": a}
                               for e, p, a in apps]}}
    try:
        # On ecrit d'abord un fichier temporaire, puis on le renomme : une
        # coupure de courant en plein enregistrement ne peut donc pas
        # laisser un profils.json a moitie ecrit.
        temporaire = C.PROFILES_FILE + ".tmp"
        with open(temporaire, "w") as fichier:
            json.dump(data, fichier)
        import os
        try:
            os.remove(C.PROFILES_FILE)
        except OSError:
            pass
        os.rename(temporaire, C.PROFILES_FILE)
    except Exception as exc:
        return False, "ecriture impossible : %s" % exc
    return True, ""


def enregistrer_json(data, nb_touches):
    """Enregistre directement une configuration recue d'une page web."""
    try:
        profils, ordre, titres, apps, repli = depuis_json(data, nb_touches)
    except Exception as exc:
        return False, "donnees illisibles : %s" % exc
    return enregistrer(profils, ordre, titres, apps, repli, nb_touches)


def effacer():
    """Supprime le fichier : retour aux valeurs d'usine au prochain RESET."""
    try:
        import os
        os.remove(C.PROFILES_FILE)
        return True
    except OSError:
        return False
