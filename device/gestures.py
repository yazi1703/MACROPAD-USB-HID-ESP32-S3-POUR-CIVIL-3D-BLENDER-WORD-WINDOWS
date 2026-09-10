# -*- coding: utf-8 -*-
"""
gestures.py - Appui court, appui long, double appui.

=====================================================================
CE QUE CA APPORTE
=====================================================================
Chaque touche peut declencher TROIS macros differentes selon la facon
dont tu appuies :

    appui court   -> macro 1
    appui long    -> macro 2   (maintenu au-dela de GESTE_LONG_MS)
    double appui  -> macro 3   (deux appuis rapprochés)

Six touches deviennent donc dix-huit actions, sans un seul composant de
plus.

=====================================================================
LE PIEGE DU DOUBLE APPUI, ET COMMENT ON L'EVITE
=====================================================================
Pour savoir si un appui est simple ou double, il faut attendre : "est-ce
qu'un second appui arrive dans les 250 ms ?". Naivement, cela ajoute donc
250 ms de retard a TOUTES les touches. Inacceptable pour un macropad.

La solution : on ne fait attendre que les touches qui ont VRAIMENT une
macro de double appui. Une touche qui n'en a pas part instantanement au
relachement, exactement comme avant. Meme raisonnement pour l'appui long :
sans macro longue, on ne surveille rien.

C'est main.py qui declare les capacites de chaque touche, a chaque
changement de profil, avec configurer().

=====================================================================
LA MACHINE A ETATS, TOUCHE PAR TOUCHE
=====================================================================
    REPOS      --appui-->        ENFONCE
    ENFONCE    --maintenu-->     LONG_ENVOYE   (emet LONG)
    ENFONCE    --relache-->      REPOS         (emet COURT)
             ou ATTENTE_DOUBLE   si la touche a une macro double
    ATTENTE_DOUBLE --appui-->    REPOS         (emet DOUBLE)
    ATTENTE_DOUBLE --delai-->    REPOS         (emet COURT, tardif)
    LONG_ENVOYE    --relache-->  REPOS         (rien : deja emis)

L'appui long est emis DES QUE le seuil est franchi, sans attendre le
relachement : tu sens la macro partir sous ton doigt, c'est bien plus
agreable que d'attendre d'avoir relache.

=====================================================================
LE MODE MODIFICATEUR : UNE TOUCHE QUI FAIT CTRL ET MAJ
=====================================================================
Une touche dont l'appui court est du type "maintien" ne fonctionne plus
comme les autres. Elle devient une vraie touche modificatrice :

    1 appui maintenu                     -> Ctrl reste enfonce
    1 appui bref, puis 1 appui maintenu  -> Maj reste enfonce

Tu gardes le doigt dessus, le modificateur reste enfonce cote PC ; tu
relaches, il remonte. Tu peux donc cliquer a la souris pendant ce temps,
ce qui est exactement l'usage recherche dans Civil 3D (Ctrl+clic pour
selectionner, Maj+clic pour deselectionner).

Deux choix importants :

  * le modificateur descend DES L'APPUI, sans le moindre delai. Attendre
    260 ms pour savoir si un second appui arrive rendrait la touche
    inutilisable ;
  * consequence assumee : le premier appui bref de la sequence "bref puis
    maintenu" envoie un Ctrl seul, tres bref. Un Ctrl seul n'a aucun effet
    dans Windows, Civil 3D, Blender ou Word - contrairement a Alt, qui
    ouvre la barre de menus. Evite donc de mettre ALT sur le premier
    appui.

    REPOS      --appui-->        TENU1        (emet COURT : on maintient)
    TENU1      --relache-->      ATTENTE2     (emet FIN : on relache)
                              ou REPOS        s'il n'y a pas de second
    ATTENTE2   --appui-->        TENU2        (emet DOUBLE : on maintient)
    ATTENTE2   --delai-->        REPOS        (rien)
    TENU2      --relache-->      REPOS        (emet FIN)
"""

from time import ticks_diff, ticks_add

# Les trois gestes
COURT = "court"
LONG = "long"
DOUBLE = "double"
# Un quatrieme evenement, qui n'est pas un geste enregistrable : il dit
# a main.py de relacher les touches maintenues.
FIN = "fin"

# Etats internes
_REPOS = 0
_ENFONCE = 1
_ATTENTE_DOUBLE = 2
_LONG_ENVOYE = 3
_TENU1 = 4                  # mode modificateur : premier maintien
_ATTENTE_MAINTIEN2 = 5      # relache, on guette le second appui
_TENU2 = 6                  # mode modificateur : second maintien


class Gestes:
    """Transforme des appuis/relachements bruts en gestes."""

    def __init__(self, nb_touches, long_ms=400, double_ms=260):
        self.nb_touches = nb_touches
        self.long_ms = long_ms
        self.double_ms = double_ms
        self.etats = [_REPOS] * nb_touches
        self.instants = [0] * nb_touches          # debut d'appui / fin d'attente
        # Capacites, mises a jour a chaque changement de profil.
        self.a_long = [False] * nb_touches
        self.a_double = [False] * nb_touches
        # Mode modificateur (voir en tete de fichier).
        self.a_maintien = [False] * nb_touches
        self.a_maintien2 = [False] * nb_touches

    # ------------------------------------------------------------------
    def configurer(self, macros):
        """Declare quelles touches ont une macro longue ou double.

        macros est la liste (libelle, gestes) du profil courant. Une touche
        sans macro longue ne surveillera pas le maintien ; une touche sans
        macro double ne fera pas attendre le second appui.
        """
        for index in range(self.nb_touches):
            gestes = {}
            if index < len(macros):
                gestes = macros[index][1] or {}
            self.a_long[index] = bool(gestes.get(LONG))
            self.a_double[index] = bool(gestes.get(DOUBLE))
            self.a_maintien[index] = _est_maintien(gestes.get(COURT))
            self.a_maintien2[index] = _est_maintien(gestes.get(DOUBLE))
        self.reinitialiser()

    def reinitialiser(self):
        for index in range(self.nb_touches):
            self.etats[index] = _REPOS

    # ------------------------------------------------------------------
    def appui(self, index, now):
        """Un appui vient d'etre detecte. Retourne un geste ou None."""
        if not (0 <= index < self.nb_touches):
            return None
        etat = self.etats[index]

        if self.a_maintien[index]:
            # Mode modificateur : on enfonce tout de suite, sans attendre.
            if etat == _ATTENTE_MAINTIEN2:
                self.etats[index] = _TENU2
                return DOUBLE           # second maintien (Maj)
            self.etats[index] = _TENU1
            return COURT                # premier maintien (Ctrl)

        if etat == _ATTENTE_DOUBLE:
            # Second appui dans le delai : c'est un double.
            self.etats[index] = _REPOS
            return DOUBLE
        self.etats[index] = _ENFONCE
        self.instants[index] = now
        return None

    def relachement(self, index, now):
        """Un relachement vient d'etre detecte. Retourne un geste ou None."""
        if not (0 <= index < self.nb_touches):
            return None
        etat = self.etats[index]

        if etat == _TENU1:
            # On relache le modificateur, et on guette un second appui.
            if self.a_maintien2[index]:
                self.etats[index] = _ATTENTE_MAINTIEN2
                self.instants[index] = ticks_add(now, self.double_ms)
            else:
                self.etats[index] = _REPOS
            return FIN
        if etat == _TENU2:
            self.etats[index] = _REPOS
            return FIN

        if etat == _LONG_ENVOYE:
            self.etats[index] = _REPOS      # la macro longue est deja partie
            return None
        if etat != _ENFONCE:
            return None
        if self.a_double[index]:
            # On attend un eventuel second appui avant de conclure.
            self.etats[index] = _ATTENTE_DOUBLE
            self.instants[index] = ticks_add(now, self.double_ms)
            return None
        self.etats[index] = _REPOS
        return COURT

    def service(self, now):
        """A appeler a chaque tour de boucle. Retourne [(index, geste), ...]."""
        resultats = []
        for index in range(self.nb_touches):
            etat = self.etats[index]
            if etat == _ENFONCE:
                if (self.a_long[index]
                        and ticks_diff(now, self.instants[index]) >= self.long_ms):
                    self.etats[index] = _LONG_ENVOYE
                    resultats.append((index, LONG))
            elif etat == _ATTENTE_DOUBLE:
                if ticks_diff(now, self.instants[index]) >= 0:
                    self.etats[index] = _REPOS
                    resultats.append((index, COURT))
            elif etat == _ATTENTE_MAINTIEN2:
                # Le second appui n'est pas venu : rien a emettre, le
                # premier maintien a deja ete relache.
                if ticks_diff(now, self.instants[index]) >= 0:
                    self.etats[index] = _REPOS
        return resultats


def _est_maintien(actions):
    """Cette macro est-elle du type 'maintien' (touche gardee enfoncee) ?"""
    return bool(actions) and actions[0][0] == "maintien"
