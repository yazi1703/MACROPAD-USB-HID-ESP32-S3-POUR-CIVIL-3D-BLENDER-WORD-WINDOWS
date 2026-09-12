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
          "couleur": "#00a0ff",
          "touches": [
            {"label": "MATCH",
             "court":  [{"type": "text_enter", "valeur": "_MATCHPROP"}],
             "long":   [],
             "double": [{"type": "text_enter", "valeur": "_PURGE"},
                        {"type": "pause",      "valeur": "500"},
                        {"type": "combo",      "valeur": "CTRL+S"}]},
            ...
          ],
          "combos": [
            {"touches": [3, 4], "label": "VUE PREC.",
             "actions": [{"type": "text_enter", "valeur": "MPVIEWPREV"}]}
          ]
        }
      },
      "apps": {
        "repli": {"profil": "WINDOWS", "abrege": "Win"},
        "liste": [{"exe": "acad.exe", "profil": "CIVIL3D", "abrege": "C3D"}]
      }
    }

Chaque geste est une LISTE d'etapes : un appui peut taper une commande,
attendre, puis valider. Une seule etape reste le cas courant.

Le "type" vaut "key", "combo", "maintien", "pause", "text", "text_enter"
ou "none". Une "pause" attend le nombre de millisecondes indique, sans
rien bloquer.
Pour un "combo", la valeur s'ecrit avec des plus : "CTRL+SHIFT+ESC".
Un "maintien" s'ecrit pareil, mais la touche reste ENFONCEE tant que tu
gardes le doigt dessus : c'est ainsi qu'une touche du macropad devient une
vraie touche Ctrl ou Maj.

Chaque profil peut aussi porter des COMBINAISONS : deux touches appuyees
en meme temps declenchent une macro a elles. Dans le fichier, elles
s'ecrivent avec les numeros qu'on lit sur le pad - [3, 4] c'est B3 et B4 -
et non avec les indices internes qui commencent a zero.

Un profil ecrit AVANT cette version n'a pas de bloc "combos" : il recupere
alors celles d'usine. Une liste "combos" presente mais vide veut dire "je
n'en veux aucune", et elle est respectee.
"""

import json
import config as C
import profiles as P
from layouts import compile_actions

TYPES = ("key", "combo", "maintien", "pause", "text", "text_enter", "none")

# Repli si profiles.py est reste a une version anterieure : une carte dont
# on n'a televerse qu'une partie des fichiers doit demarrer, pas planter.
LABEL_COMBO_MAX = getattr(P, "COMBO_LABEL_MAX", 16)


# =====================================================================
# Conversion entre la forme des pages web et la forme interne
# =====================================================================
def action_vers_json(actions):
    """Forme interne -> (type, valeur texte) pour les formulaires."""
    if not actions:
        return "none", ""
    genre, valeur = actions[0]
    if genre in ("combo", "maintien"):
        # Les deux transportent une liste de touches : CTRL+MAJ, ou juste CTRL.
        return genre, "+".join(valeur)
    return genre, str(valeur)


def actions_vers_json(actions):
    """Forme interne -> LISTE de {"type", "valeur"} pour les formulaires.

    Un geste peut enchainer plusieurs frappes : taper une commande,
    attendre que la boite de dialogue s'ouvre, puis valider. Chaque etape
    est une entree de cette liste.
    """
    liste = []
    for action in (actions or []):
        genre, valeur = action_vers_json([action])
        liste.append({"type": genre, "valeur": valeur})
    return liste


def actions_depuis_json(champ):
    """Forme web -> forme interne. Accepte une liste OU une seule action.

    L'ancienne forme - un seul dictionnaire par geste - reste acceptee :
    un profils.json ecrit avant les sequences se relit sans rien perdre.
    """
    if not champ:
        return []
    if isinstance(champ, dict):
        champ = [champ]
    actions = []
    for etape in champ:
        if not isinstance(etape, dict):
            raise ValueError("etape illisible : " + repr(etape))
        actions.extend(action_depuis_json(etape.get("type", "none"),
                                          etape.get("valeur", "")))
    return actions


def action_depuis_json(genre, valeur):
    """(type, valeur texte) -> forme interne."""
    if genre == "none" or (genre in ("text", "text_enter") and not valeur):
        return []
    if genre in ("combo", "maintien"):
        touches = tuple(p.strip() for p in str(valeur).split("+") if p.strip())
        if not touches:
            raise ValueError("combinaison vide")
        return [(genre, touches)]
    if genre == "pause":
        if not str(valeur).strip():
            return []
        return [("pause", str(valeur).strip())]
    if genre in ("key", "text", "text_enter"):
        if not str(valeur).strip():
            return []
        return [(genre, str(valeur))]
    raise ValueError("type inconnu : " + str(genre))


# =====================================================================
# Les combinaisons de touches
# =====================================================================
def nom_combo(indices):
    """(2, 3) -> "B3+B4" : le nom qu'on lit sur le pad.

    combos.py a la meme fonction, volontairement : store.py doit rester
    lisible sans le module de saisie, qui lui parle a l'horloge de la carte.
    """
    return "+".join("B%d" % (int(index) + 1) for index in indices)


def combos_vers_json(combos):
    """Forme interne -> liste JSON, avec des numeros de touches lisibles.

    En interne les touches sont numerotees a partir de zero, comme partout
    ailleurs en informatique. Dans le fichier et dans les pages web elles
    portent le numero grave sur le pad. La conversion se fait ici, une
    bonne fois pour toutes.
    """
    liste = []
    for indices, label, actions in (combos or []):
        liste.append({"touches": [int(index) + 1 for index in indices],
                      "label": str(label),
                      "actions": actions_vers_json(actions)})
    return liste


def combos_depuis_json(champ):
    """Liste JSON -> forme interne. Leve une exception si c'est illisible.

    On ne corrige rien ici : les doublons et les numeros farfelus sont
    conserves tels quels pour que verifier() puisse les nommer dans un
    message clair, plutot que de les faire disparaitre en silence.
    """
    combos = []
    for entree in (champ or []):
        if not isinstance(entree, dict):
            raise ValueError("combinaison illisible : " + repr(entree))
        touches = entree.get("touches") or []
        if not isinstance(touches, (list, tuple)):
            raise ValueError("combinaison : 'touches' n'est pas une liste")
        indices = tuple(sorted(int(numero) - 1 for numero in touches))
        combos.append((indices,
                       str(entree.get("label", ""))[:LABEL_COMBO_MAX],
                       actions_depuis_json(entree.get("actions"))))
    return combos


def combos_usine():
    """Copie des combinaisons d'usine, profil par profil."""
    table = {}
    # getattr : un profiles.py televerse depuis une version anterieure n'a
    # pas de table COMBOS. Le firmware demarre quand meme, sans
    # combinaisons, plutot que de refuser de booter.
    for nom, liste in getattr(P, "COMBOS", {}).items():
        table[nom] = [(tuple(indices), label, list(actions))
                      for indices, label, actions in liste]
    return table


# =====================================================================
# Les couleurs des LED RGB
# =====================================================================
# Dans le fichier et dans les pages web, une couleur s'ecrit comme en
# HTML : "#00a0ff". C'est ce que comprend le selecteur de couleur du
# navigateur, et c'est lisible a l'oeil nu dans profils.json.
def couleur_vers_texte(couleur):
    r, v, b = (int(c) & 255 for c in couleur)
    return "#%02x%02x%02x" % (r, v, b)


def couleur_depuis_texte(texte, defaut=None):
    """Accepte "#00a0ff" ou "00a0ff". Retombe sur defaut si c'est illisible.

    On ne leve PAS d'exception ici : une couleur fausse ne doit pas
    empecher d'enregistrer des macros parfaitement valables. Au pire, le
    pad s'allume dans la couleur par defaut.
    """
    if defaut is None:
        defaut = tuple(C.RGB_COULEUR_DEFAUT)
    texte = str(texte or "").strip().lstrip("#")
    if len(texte) != 6:
        return tuple(defaut)
    try:
        return tuple(int(texte[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return tuple(defaut)


def couleur_usine(nom):
    """Couleur d'usine d'un profil, ou la couleur par defaut."""
    return tuple(getattr(C, "RGB_COULEURS", {}).get(
        nom, C.RGB_COULEUR_DEFAUT))


def couleur_usine2(nom):
    """Seconde couleur d'usine d'un profil, ou None s'il n'en a pas.

    None veut dire "pas d'alternance" : le profil respire dans sa couleur
    unique. C'est le cas de tous les profils absents de RGB_COULEURS2.
    """
    couleur = getattr(C, "RGB_COULEURS2", {}).get(nom)
    return tuple(couleur) if couleur else None


# =====================================================================
# Verification
# =====================================================================
def _meme_doigt(indices):
    """(index_a, index_b, nom du doigt) si deux touches le partagent, sinon None.

    config.DOIGTS peut etre absente ou None : le controle est alors
    silencieusement saute, et rien ne se casse.
    """
    doigts = getattr(C, "DOIGTS", None)
    if not doigts:
        return None
    for rang, index in enumerate(indices):
        for autre in indices[rang + 1:]:
            if (0 <= index < len(doigts) and 0 <= autre < len(doigts)
                    and doigts[index] == doigts[autre]):
                return index, autre, doigts[index]
    return None


def verifier_combos(combos, profils, nb_touches):
    """Verifie les combinaisons d'un profil. Retourne la liste des problemes."""
    problemes = []
    for nom, liste in (combos or {}).items():
        if nom not in profils:
            problemes.append("combinaisons : le profil '%s' n'existe pas" % nom)
        deja = {}
        for indices, label, actions in (liste or []):
            touches = nom_combo(indices)
            if len(set(indices)) != len(indices):
                problemes.append("%s %s : la meme touche est citee deux fois"
                                 % (nom, touches))
                continue
            if len(indices) < 2:
                # Une "combinaison" d'une seule touche rendrait cette touche
                # inutilisable seule : ce n'en est pas une.
                problemes.append("%s %s : il faut au moins deux touches"
                                 % (nom, touches))
                continue
            hors = [index for index in indices if not 0 <= index < nb_touches]
            if hors:
                problemes.append("%s %s : la touche B%d n'existe pas"
                                 % (nom, touches, hors[0] + 1))
                continue
            cle = tuple(sorted(indices))
            if cle in deja:
                problemes.append("%s %s : deja prise par '%s'"
                                 % (nom, touches, deja[cle]))
                continue
            deja[cle] = label
            memes = _meme_doigt(indices)
            if memes:
                # Le seul controle qui parle du MONDE PHYSIQUE plutot que
                # du fichier : un doigt ne peut pas appuyer deux touches a
                # la fois. La combinaison serait muette, pas fausse - le
                # pire des defauts a diagnostiquer.
                problemes.append("%s %s : B%d et B%d sont sous le meme doigt "
                                 "(%s), impossible a appuyer ensemble"
                                 % (nom, touches, memes[0] + 1, memes[1] + 1,
                                    memes[2]))
            if len(label) > LABEL_COMBO_MAX:
                problemes.append("%s %s : libelle '%s' depasse %d caracteres"
                                 % (nom, touches, label, LABEL_COMBO_MAX))
            for genre, _valeur in (actions or []):
                if genre == "maintien":
                    # Un maintien se relache quand SA touche se relache. Une
                    # combinaison n'a pas de touche unique a surveiller : le
                    # Ctrl resterait enfonce pour de bon. Interdit, donc.
                    problemes.append("%s %s : un 'maintien' est impossible "
                                     "dans une combinaison (la touche "
                                     "resterait enfoncee)" % (nom, touches))
                    break
            try:
                compile_actions(actions, C.KEYBOARD_LAYOUT)
            except Exception as exc:
                problemes.append("%s %s (%s) : %s" % (nom, touches, label, exc))
    return problemes


def verifier(profils, ordre, nb_touches, combos=None):
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

    problemes.extend(verifier_combos(combos, profils, nb_touches))
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
    couleurs = dict((nom, couleur_usine(nom)) for nom in profils)
    couleurs2 = dict((nom, couleur_usine2(nom)) for nom in profils)
    return (profils, list(C.PROFILES_ORDER), dict(P.TITLES), couleurs,
            couleurs2, combos_usine(), apps, tuple(P.APPS_REPLI))


# =====================================================================
# Conversion vers et depuis les pages web
# =====================================================================
def vers_json(nb_touches, stats=None):
    """Configuration complete, prete a etre envoyee a une page web."""
    (profils, ordre, titres, couleurs, couleurs2, combos,
     apps, repli, origine) = charger(nb_touches)
    blocs = {}
    for nom, touches in profils.items():
        liste = []
        for index, (label, gestes) in enumerate(touches):
            entree = {"label": label}
            for geste in P.GESTES:
                entree[geste] = actions_vers_json((gestes or {}).get(geste))
            if stats is not None:
                entree["usages"] = stats.pour(nom)[index]
            liste.append(entree)
        blocs[nom] = {
            "titre": titres.get(nom, nom),
            "couleur": couleur_vers_texte(
                couleurs.get(nom) or couleur_usine(nom)),
            # Chaine vide = aucune seconde couleur, donc aucune alternance.
            "couleur2": (couleur_vers_texte(couleurs2.get(nom))
                         if couleurs2.get(nom) else ""),
            "touches": liste,
            "combos": combos_vers_json(combos.get(nom)),
        }

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
    profils, titres, couleurs, combos = {}, {}, {}, {}
    couleurs2 = {}
    usine = combos_usine()
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
                actions = actions_depuis_json(entree.get(geste))
                if actions:
                    gestes[geste] = actions
            touches.append((str(entree.get("label", ""))[:P.LABEL_MAX], gestes))
        while len(touches) < nb_touches:
            touches.append(("", {}))
        profils[str(nom)] = touches
        titres[str(nom)] = str(bloc.get("titre", nom))
        couleurs[str(nom)] = couleur_depuis_texte(bloc.get("couleur"),
                                                  couleur_usine(str(nom)))
        if "couleur2" in bloc:
            texte = str(bloc.get("couleur2") or "").strip()
            couleurs2[str(nom)] = (couleur_depuis_texte(texte)
                                   if texte else None)
        else:
            # Fichier ecrit avant l'alternance : on remet celle d'usine,
            # comme pour les combinaisons. Une chaine VIDE, elle, veut dire
            # "pas d'alternance" et est respectee.
            couleurs2[str(nom)] = couleur_usine2(str(nom))
        if "combos" in bloc:
            combos[str(nom)] = combos_depuis_json(bloc.get("combos"))
        else:
            # Fichier ecrit avant les combinaisons : on remet celles d'usine
            # plutot que de les faire disparaitre a la premiere mise a jour.
            # Une liste presente mais VIDE, elle, est respectee.
            combos[str(nom)] = usine.get(str(nom), [])

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
    return profils, ordre, titres, couleurs, couleurs2, combos, apps, repli


# =====================================================================
# Lecture et ecriture du fichier
# =====================================================================
def charger(nb_touches):
    """Retourne (profils, ordre, titres, couleurs, couleurs2, combos, apps,
    repli, origine).

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
        (profils, ordre, titres, couleurs, couleurs2, combos,
         apps, repli) = depuis_json(data, nb_touches)
    except Exception as exc:
        print("[store] %s mal forme (%s), retour aux valeurs d'usine"
              % (C.PROFILES_FILE, exc))
        return defauts() + ("usine",)

    problemes = verifier(profils, ordre, nb_touches, combos)
    if problemes:
        print("[store] %s refuse, retour aux valeurs d'usine :" % C.PROFILES_FILE)
        for probleme in problemes:
            print("   -", probleme)
        return defauts() + ("usine",)

    return (profils, ordre, titres, couleurs, couleurs2, combos, apps, repli,
            "fichier")


def enregistrer(profils, ordre, titres, couleurs, couleurs2, combos, apps,
                repli, nb_touches):
    """Verifie puis ecrit. Retourne (True, "") ou (False, raison)."""
    problemes = verifier(profils, ordre, nb_touches, combos)
    if problemes:
        return False, " ; ".join(problemes)

    blocs = {}
    for nom, touches in profils.items():
        liste = []
        for label, gestes in touches:
            entree = {"label": label}
            for geste in P.GESTES:
                entree[geste] = actions_vers_json((gestes or {}).get(geste))
            liste.append(entree)
        blocs[nom] = {
            "titre": titres.get(nom, nom),
            "couleur": couleur_vers_texte(
                (couleurs or {}).get(nom) or couleur_usine(nom)),
            "couleur2": (couleur_vers_texte((couleurs2 or {}).get(nom))
                         if (couleurs2 or {}).get(nom) else ""),
            "touches": liste,
            "combos": combos_vers_json((combos or {}).get(nom)),
        }

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
        (profils, ordre, titres, couleurs, couleurs2, combos,
         apps, repli) = depuis_json(data, nb_touches)
    except Exception as exc:
        return False, "donnees illisibles : %s" % exc
    return enregistrer(profils, ordre, titres, couleurs, couleurs2, combos,
                       apps, repli, nb_touches)


def effacer():
    """Supprime le fichier : retour aux valeurs d'usine au prochain RESET."""
    try:
        import os
        os.remove(C.PROFILES_FILE)
        return True
    except OSError:
        return False
