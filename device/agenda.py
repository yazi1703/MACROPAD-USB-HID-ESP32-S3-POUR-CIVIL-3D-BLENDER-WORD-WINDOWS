# -*- coding: utf-8 -*-
"""
agenda.py - La journee du jour, telle que le PC la raconte a la carte.

=====================================================================
CE FICHIER NE DESSINE RIEN
=====================================================================
Il ne connait ni l'ecran, ni le port serie. Il repond a quatre questions,
et rien d'autre :

    quelle heure est-il ?           minute(now)
    qu'est-ce qui est en cours ?    courant(minute)
    qu'est-ce qui vient ensuite ?   prochain(minute)
    que montrer dans la fenetre ?   fenetre(minute)

C'est ce qui le rend testable sur un PC, sans carte et sans ecran : tous
les cas penibles - un evenement a cheval sur minuit, une heure perimee,
deux reunions qui se chevauchent - se verifient en une milliseconde.

=====================================================================
LA CARTE N'A PAS D'HORLOGE, ET C'EST IMPORTANT
=====================================================================
L'ESP32-S3 n'a aucune pile de sauvegarde : au branchement, il ne sait ni
l'heure ni la date. C'est le compagnon PC qui les lui envoie, toutes les
minutes.

Entre deux messages, on extrapole avec ticks_ms() - c'est fiable a la
seconde pres sur quelques minutes. Mais si le compagnon se TAIT (PC en
veille, cable debranche, programme ferme), cette extrapolation derive
sans que rien ne le signale.

D'ou la regle, et elle est absolue : au-dela de AGENDA_HEURE_PERIMEE_MS
sans nouvelle, minute() renvoie None. L'ecran affiche alors "--:--" et
efface la ligne "maintenant". UNE HEURE FAUSSE EST PIRE QUE PAS D'HEURE :
elle te ferait rater une reunion en te croyant a l'heure.

=====================================================================
LE FORMAT RECU
=====================================================================
    H:19:47|DIM 13              l'heure et le libelle du jour
    !AGBEGIN                    debut de la liste
    A:16:00|17:00|ELDV - Etude et modelisation 3D
    A:19:30|21:00|tache 1
    !AGEND                      fin : la liste remplace l'ancienne

La liste n'est adoptee qu'a !AGEND : une transmission coupee en deux ne
laisse jamais un agenda a moitie efface a l'ecran.
"""

from time import ticks_ms, ticks_diff
import config as C

MINUTES_PAR_JOUR = 24 * 60


def minutes_depuis_texte(texte):
    """'19:47' -> 1187. None si ce n'est pas une heure valable.

    On ne devine rien : une entree illisible vaut None, et l'appelant
    decide quoi en faire. Une heure inventee serait pire que pas d'heure.
    """
    try:
        heures, minutes = str(texte).strip().split(":")
        heures, minutes = int(heures), int(minutes)
    except Exception:
        return None
    if not (0 <= heures <= 23 and 0 <= minutes <= 59):
        return None
    return heures * 60 + minutes


def texte_depuis_minutes(minute):
    """1187 -> '19:47'. '--:--' si on ne sait pas."""
    if minute is None:
        return "--:--"
    minute = int(minute) % MINUTES_PAR_JOUR
    return "%02d:%02d" % (minute // 60, minute % 60)


class Agenda:
    """Ce que la carte sait de ta journee. Rien de plus."""

    def __init__(self):
        self.jour = ""              # "DIM 13", tel que le PC l'envoie
        self.evenements = []        # [(debut, fin, titre), ...] tries
        self._minute = None         # minute du jour au dernier message
        self._recu = 0              # ticks_ms de ce message
        self._en_cours = None       # liste en cours de reception

    # ------------------------------------------------------------------
    # L'heure
    # ------------------------------------------------------------------
    def set_heure(self, texte, now=None):
        """Traite 'H:19:47|DIM 13'. Retourne True si c'est exploitable."""
        texte = str(texte or "")
        if "|" in texte:
            heure, jour = texte.split("|", 1)
        else:
            heure, jour = texte, self.jour
        minute = minutes_depuis_texte(heure)
        if minute is None:
            return False
        self._minute = minute
        self._recu = ticks_ms() if now is None else now
        self.jour = str(jour).strip()[:10]
        return True

    def minute(self, now=None):
        """La minute du jour, ou None si on ne peut plus la garantir.

        Entre deux messages du PC on extrapole avec l'horloge interne.
        Au-dela de AGENDA_HEURE_PERIMEE_MS, on ne garantit plus rien et on
        le dit, plutot que d'afficher une heure qui a derive.
        """
        if self._minute is None:
            return None
        now = ticks_ms() if now is None else now
        ecart = ticks_diff(now, self._recu)
        if ecart < 0:
            ecart = 0
        if ecart > getattr(C, "AGENDA_HEURE_PERIMEE_MS", 300000):
            return None
        return (self._minute + ecart // 60000) % MINUTES_PAR_JOUR

    def heure_perimee(self, now=None):
        """A-t-on deja eu l'heure, mais plus assez recemment ?

        Sert a distinguer deux messages a l'ecran : "le PC ne m'a jamais
        parle" et "le PC s'est taise". Ce n'est pas la meme panne.
        """
        return self._minute is not None and self.minute(now) is None

    # ------------------------------------------------------------------
    # La liste des evenements
    # ------------------------------------------------------------------
    def commencer(self):
        """!AGBEGIN : on ouvre une liste neuve, sans toucher a l'ancienne."""
        self._en_cours = []

    def ajouter(self, texte):
        """A:16:00|17:00|ELDV - Etude : une ligne de la liste en cours.

        Une ligne illisible est ignoree en silence - une reunion perdue
        vaut mieux qu'un agenda refuse en entier - mais elle n'annule pas
        la transmission.
        """
        if self._en_cours is None:
            return False
        if len(self._en_cours) >= getattr(C, "AGENDA_MAX", 16):
            return False
        morceaux = str(texte or "").split("|", 2)
        if len(morceaux) < 3:
            return False
        debut = minutes_depuis_texte(morceaux[0])
        fin = minutes_depuis_texte(morceaux[1])
        titre = morceaux[2].strip()[:getattr(C, "AGENDA_TITRE_MAX", 40)]
        if debut is None or fin is None or not titre:
            return False
        # Une reunion qui finit avant de commencer passe minuit. On la
        # borne a la fin de la journee : l'ecran ne montre qu'aujourd'hui.
        if fin <= debut:
            fin = MINUTES_PAR_JOUR - 1
        self._en_cours.append((debut, fin, titre))
        return True

    def terminer(self):
        """!AGEND : la liste recue remplace l'ancienne, d'un seul coup.

        C'est ici, et nulle part avant, que l'ecran change. Une liaison
        coupee au milieu d'une transmission laisse donc l'agenda PRECEDENT
        affiche, pas un agenda a moitie vide.
        """
        if self._en_cours is None:
            return False
        self.evenements = sorted(self._en_cours)
        self._en_cours = None
        return True

    # ------------------------------------------------------------------
    # Les questions que l'ecran pose
    # ------------------------------------------------------------------
    def courant(self, minute):
        """L'evenement en cours a cette minute, ou None.

        Si deux se chevauchent - ca arrive, on est invite a deux reunions
        en meme temps - on rend celui qui finit le plus tot : c'est celui
        dont l'echeance presse.
        """
        if minute is None:
            return None
        en_cours = [e for e in self.evenements if e[0] <= minute < e[1]]
        if not en_cours:
            return None
        return min(en_cours, key=lambda e: e[1])

    def prochain(self, minute):
        """Le premier evenement qui n'a pas encore commence, ou None."""
        if minute is None:
            return None
        for evenement in self.evenements:
            if evenement[0] > minute:
                return evenement
        return None

    def fenetre(self, minute):
        """(heure_de_depart, evenements visibles) pour la vue timeline.

        La fenetre glisse avec l'heure : une heure de passe, le reste en
        avenir. On n'a rien a regler, et le passe s'en va tout seul.
        """
        heures = getattr(C, "AGENDA_FENETRE_H", 5)
        avant = getattr(C, "AGENDA_AVANT_H", 1)
        if minute is None:
            # Sans heure, on montre le debut de la journee plutot que rien :
            # la liste reste lisible, seule la ligne "maintenant" manque.
            depart = self.evenements[0][0] // 60 if self.evenements else 8
        else:
            depart = minute // 60 - avant
        if depart < 0:
            depart = 0
        if depart + heures > 24:
            depart = 24 - heures
        debut, fin = depart * 60, (depart + heures) * 60
        visibles = [e for e in self.evenements if e[1] > debut and e[0] < fin]
        return depart, visibles

    def resume(self, minute, now=None):
        """La ligne du bas : (prefixe fixe, intitule qui defile).

        Quatre situations, quatre reponses :
          - une reunion est EN COURS  -> quand finit-elle
          - une reunion approche      -> dans combien de temps
          - plus rien aujourd'hui     -> le dire, et ne pas laisser vide
          - pas d'heure               -> dire LAQUELLE des deux pannes
        """
        if minute is None:
            # DEUX PANNES DIFFERENTES, DEUX MESSAGES, ET CA COMPTE.
            # "Ne repond plus" sous-entend qu'il repondait AVANT : le dire
            # a quelqu'un dont le compagnon n'a jamais parle l'envoie
            # chercher une panne de liaison qui n'existe pas. Le vrai
            # defaut est alors bien plus simple - le compagnon tourne sans
            # l'option --agenda - et le message doit le dire.
            if self.heure_perimee(now):
                return ("", "Le PC ne repond plus")
            return ("", "En attente du PC - lance-le avec --agenda")
        # L'HEURE DE DEBUT, TOUJOURS. Une premiere version montrait la
        # fin d'une reunion en cours et un compte a rebours pour la
        # suivante : trois reperes differents sur la meme ligne, qu'il
        # fallait interpreter a chaque coup d'oeil. Une seule regle se lit
        # sans y penser, et c'est ce qu'on demande a un ecran qu'on
        # regarde en travaillant.
        actuel = self.courant(minute)
        if actuel is not None:
            # L'etoile dit "c'est commence" - sans elle, 19:30 affiche a
            # 19:47 se lirait comme un rendez-vous a venir.
            return ("*" + texte_depuis_minutes(actuel[0]), actuel[2])
        suivant = self.prochain(minute)
        if suivant is None:
            return ("", "Plus rien aujourd'hui")
        return (texte_depuis_minutes(suivant[0]), suivant[2])
