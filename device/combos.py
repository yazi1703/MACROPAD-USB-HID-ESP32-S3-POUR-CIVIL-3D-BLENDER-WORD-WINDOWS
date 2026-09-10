# -*- coding: utf-8 -*-
"""
combos.py - Plusieurs touches appuyees EN MEME TEMPS = une macro.

=====================================================================
CE QUE CA FAIT
=====================================================================
B3+B4 ensemble declenchent une macro a eux, et surtout PAS la macro de
B3 suivie de celle de B4. Six touches offrent ainsi quinze paires, sans
un composant de plus - et l'architecture accepte deja trois ou quatre
touches simultanees le jour ou tu en voudras.

=====================================================================
LE PROBLEME, ET POURQUOI IL NE COUTE RIEN ICI
=====================================================================
Pour savoir que "B3 seule" n'est pas le debut de "B3+B4", il faut bien
attendre un peu apres B3. Naivement, cela ajoute donc un retard a toutes
les touches. Inacceptable.

Deux choses sauvent la mise :

1. SEULES LES TOUCHES MEMBRES d'une combinaison sont surveillees. B1 et
   B2 ne passent meme pas par ce fichier.

2. UN APPUI COURT PART DEJA AU RELACHEMENT, pas a l'appui. Donc :
     - tu tapes vite -> la touche est relachee AVANT la fin de la
       fenetre : on libere tout immediatement, zero retard ;
     - tu la gardes enfoncee -> l'appui est transmis a la fin de la
       fenetre, mais AVEC SON HORODATAGE D'ORIGINE. L'appui long part
       donc toujours a GESTE_LONG_MS pile.

   Cet horodatage d'origine est la piece maitresse : sans lui, un appui
   long sur une touche membre partirait en retard.

Resultat : aucune latence ajoutee, sur aucune touche.

=====================================================================
LA MACHINE A ETATS
=====================================================================
    LIBRE     --appui d'une membre-->     CANDIDAT
                                          (on retient, fenetre ouverte)

    CANDIDAT  --appui d'une autre-->      on ajoute a l'ensemble ;
                                          s'il correspond a une
                                          combinaison ET qu'aucune plus
                                          grande ne peut encore se
                                          former -> DECLENCHE

    CANDIDAT  --fin de fenetre-->         correspondance : declenche.
                                          sinon : on libere les appuis
                                          retenus -> LIBRE

    CANDIDAT  --relachement-->            c'etait un appui seul : on
                                          libere tout -> LIBRE

    CONSOMME  --toutes relachees-->       LIBRE

Pendant CONSOMME, les autres touches de combinaison sont ignorees :
rouler les doigts sur le pad en relachant ne doit pas declencher une
seconde combinaison par accident.

=====================================================================
CE QUI EST GARANTI
=====================================================================
* ESC et changement de profil : reinitialiser() abandonne tout SANS
  rien declencher et sans transmettre les appuis retenus ;
* aucune touche ne peut rester enfoncee cote PC : une combinaison
  declenche une macro ordinaire, avec les memes garanties que le reste ;
* l'ordre des doigts n'a pas d'importance : B3+B4 et B4+B3 sont la meme
  combinaison.
"""

from time import ticks_diff, ticks_add

# Etats
_LIBRE = 0
_CANDIDAT = 1
_CONSOMME = 2

# Fronts transmis a la machine a gestes
APPUI = 1
RELACHEMENT = -1


def nom_touches(cle):
    """(2, 3) -> "B3+B4", pour l'ecran."""
    return "+".join("B%d" % (index + 1) for index in cle)


class Combos:
    """Reconnait les appuis simultanes, et laisse passer le reste."""

    def __init__(self, nb_touches, fenetre_ms=50):
        self.nb_touches = nb_touches
        self.fenetre_ms = fenetre_ms
        self.table = {}                          # cle triee -> (libelle, actions)
        self.membres = [False] * nb_touches
        self.occupees = [False] * nb_touches     # consommees, pas encore relachees
        self.ignorees = [False] * nb_touches     # appuyees pendant CONSOMME
        self.retenus = []                        # [(index, instant), ...]
        self.echeance = 0
        self.etat = _LIBRE

    # ------------------------------------------------------------------
    def configurer(self, combos):
        """Declare les combinaisons du profil courant.

        combos : liste de (indices, libelle, actions). Les indices sont
        ceux des touches, a partir de zero.
        """
        self.table = {}
        self.membres = [False] * self.nb_touches
        for indices, libelle, actions in (combos or []):
            propres = []
            for index in indices:
                index = int(index)
                if 0 <= index < self.nb_touches and index not in propres:
                    propres.append(index)
            # Une "combinaison" d'une seule touche n'en est pas une : ce
            # serait un appui ordinaire, et elle rendrait la touche
            # inutilisable seule.
            if len(propres) < 2:
                continue
            propres.sort()
            self.table[tuple(propres)] = (libelle, actions)
            for index in propres:
                self.membres[index] = True
        self.reinitialiser()

    def reinitialiser(self):
        """Tout abandonner sans rien declencher (ESC, changement de profil)."""
        self.etat = _LIBRE
        self.retenus = []
        for index in range(self.nb_touches):
            self.occupees[index] = False
            self.ignorees[index] = False

    # ------------------------------------------------------------------
    def appui(self, index, now):
        """Retourne (combinaison, evenements a transmettre)."""
        if not (0 <= index < self.nb_touches):
            return None, [(APPUI, index, now)]

        if self.etat == _CONSOMME:
            if self.membres[index]:
                self.ignorees[index] = True
                return None, []
            return None, [(APPUI, index, now)]

        if not self.membres[index]:
            # Cette touche n'entre dans aucune combinaison : rien ne la
            # retarde, jamais.
            return None, [(APPUI, index, now)]

        if self.etat == _LIBRE:
            self.etat = _CANDIDAT
            self.retenus = [(index, now)]
            self.echeance = ticks_add(now, self.fenetre_ms)
            return None, []

        # _CANDIDAT
        if ticks_diff(now, self.echeance) >= 0:
            # Fenetre deja expiree : ce n'est pas une combinaison. On
            # libere ce qui etait retenu, et cette touche-ci ouvre une
            # nouvelle fenetre.
            differes = self._liberer()
            self.etat = _CANDIDAT
            self.retenus = [(index, now)]
            self.echeance = ticks_add(now, self.fenetre_ms)
            return None, differes

        self.retenus.append((index, now))
        return self._resoudre(False), []

    def relachement(self, index, now):
        """Retourne (None, evenements a transmettre)."""
        if not (0 <= index < self.nb_touches):
            return None, [(RELACHEMENT, index, now)]

        if self.occupees[index]:
            # Une touche de la combinaison qu'on vient de declencher.
            self.occupees[index] = False
            if not self._reste_occupee():
                self.etat = _LIBRE
            return None, []

        if self.ignorees[index]:
            self.ignorees[index] = False
            return None, []

        if self.etat == _CANDIDAT and self._est_retenue(index):
            # Relachee avant la fin de la fenetre : c'etait bien un appui
            # seul. On libere immediatement - c'est ce qui garantit zero
            # latence sur une tape rapide.
            differes = self._liberer()
            differes.append((RELACHEMENT, index, now))
            return None, differes

        return None, [(RELACHEMENT, index, now)]

    def service(self, now):
        """A appeler a chaque tour de boucle, comme gestes.service()."""
        if self.etat != _CANDIDAT:
            return None, []
        if ticks_diff(now, self.echeance) < 0:
            return None, []
        # La fenetre se ferme : on tranche.
        combinaison = self._resoudre(True)
        if combinaison is not None:
            return combinaison, []
        return None, self._liberer()

    # ------------------------------------------------------------------
    def _resoudre(self, forcer):
        """Declenche si l'ensemble retenu correspond a une combinaison.

        forcer=False : on attend encore si une combinaison PLUS GRANDE
        peut se former (B3+B4 alors que B3+B4+B5 existe). C'est ce qui
        permettra d'ajouter des combinaisons a trois touches sans rien
        reecrire, tout en declenchant les paires sans attendre quand
        aucune ambiguite n'existe.
        """
        cle = self._cle()
        entree = self.table.get(cle)
        if entree is None:
            return None
        if not forcer and self._peut_grandir(cle):
            return None
        for index, _instant in self.retenus:
            self.occupees[index] = True
        self.retenus = []
        self.etat = _CONSOMME
        return (cle, entree[0], entree[1])

    def _peut_grandir(self, cle):
        for autre in self.table:
            if len(autre) <= len(cle):
                continue
            complet = True
            for index in cle:
                if index not in autre:
                    complet = False
                    break
            if complet:
                return True
        return False

    def _liberer(self):
        """Transmet les appuis retenus, AVEC LEUR HORODATAGE D'ORIGINE."""
        differes = [(APPUI, index, instant) for index, instant in self.retenus]
        self.retenus = []
        self.etat = _LIBRE
        return differes

    def _cle(self):
        indices = [index for index, _instant in self.retenus]
        indices.sort()
        return tuple(indices)

    def _est_retenue(self, index):
        for retenu, _instant in self.retenus:
            if retenu == index:
                return True
        return False

    def _reste_occupee(self):
        for occupee in self.occupees:
            if occupee:
                return True
        return False
