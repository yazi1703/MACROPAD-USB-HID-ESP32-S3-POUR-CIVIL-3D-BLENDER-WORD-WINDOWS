# -*- coding: utf-8 -*-
"""
joystick.py - Le stick analogique, traduit en mouvement de vue 3D.

=====================================================================
CE FICHIER NE TOUCHE AUCUN MATERIEL
=====================================================================
Il ne lit aucune broche, il n'envoie rien par USB, il ne connait ni
l'ecran ni le port serie. On lui donne DEUX NOMBRES - la position brute
des deux axes - et il repond ce qu'il faut faire.

C'est ce qui le rend testable sur un PC, sans carte et sans joystick :
tous les cas penibles - un centre decale, un axe inverse, le stick qui
traverse le centre au milieu d'un mouvement - se verifient en une
milliseconde.

Le meme choix a ete fait pour agenda.py, et pour la meme raison.

=====================================================================
POURQUOI UNE "MACHINE A ETATS" ET PAS UN SIMPLE CALCUL
=====================================================================
Tourner une vue 3D, ce n'est pas "deplacer la souris". Dans tous les
logiciels, c'est un GLISSEMENT : on enfonce un bouton, on deplace, on
relache. Trois moments differents, et l'ordre compte.

    repos      le stick est au milieu, rien n'est enfonce
    debut      le stick sort du milieu -> enfoncer le bouton
    glissement -> envoyer des petits deplacements
    fin        le stick est revenu au milieu -> relacher le bouton

Un simple calcul "position -> deplacement" ne saurait pas ou enfoncer ni
ou relacher. D'ou les quatre etats ci-dessous.

=====================================================================
LE PIEGE DU RETOUR AU CENTRE
=====================================================================
Quand tu passes d'une rotation vers la gauche a une rotation vers la
droite, le stick TRAVERSE le centre. Pendant un instant tres court, il
est donc "au repos".

Sans precaution, le glissement serait coupe en deux : bouton relache,
bouton re-enfonce. Dans Blender cela termine l'orbite et en commence une
autre - la vue saute. D'ou JOYSTICK_FIN_MS : on n'accepte la fin d'un
glissement qu'apres un court sejour au repos.

=====================================================================
VOCABULAIRE
=====================================================================
  brut        ce que rend read_u16() : un entier de 0 a 65535
  centre      la valeur brute du stick AU REPOS. Elle ne vaut jamais
              32768 : chaque exemplaire a la sienne, d'ou l'etalonnage.
  fraction    la position ramenee entre -1.0 et +1.0, zone morte deduite
  zone morte  la plage autour du centre ou l'on considere le stick immobile
  cadence     le temps minimal entre deux envois (l'USB ne suit pas au-dela)
"""

from time import ticks_ms, ticks_diff, ticks_add
import config as C

# Ce que rend read_u16() au maximum. C'est l'echelle de MicroPython, pas
# celle du convertisseur : la bibliotheque etire toujours la mesure sur
# seize bits, quelle que soit la resolution reelle du materiel.
PLEINE_ECHELLE = 65535

# Un rapport de souris USB ne transporte qu'un octet signe par axe. Au-dela,
# la bibliotheque leve ValueError - voir la note dans hid_mouse.py.
DEPLACEMENT_MAX = 127

# Les quatre etats du glissement.
REPOS = "repos"
GLISSE = "glisse"

# Ce que service() demande a main.py de faire. main.py est le seul a savoir
# comment parler a l'USB ; ce fichier ne fait que nommer l'intention.
RIEN = "rien"
COMMENCER = "commencer"      # enfoncer le modificateur puis le bouton
BOUGER = "bouger"            # envoyer (dx, dy)
TERMINER = "terminer"        # relacher le bouton puis le modificateur

# Les modes possibles, et ils sont verifies : une valeur inconnue venant
# d'un profils.json bricole a la main ne doit pas faire tomber la carte.
MODE_ETEINT = "eteint"
MODE_SOURIS = "souris"
MODE_TOUCHES = "touches"
MODES = (MODE_ETEINT, MODE_SOURIS, MODE_TOUCHES)

# Ce qui peut etre maintenu pendant le glissement. C'est le seul reglage
# qui distingue Blender de Civil 3D : dans l'un l'orbite est le clic du
# milieu seul, dans l'autre c'est Maj + clic du milieu.
MODIFICATEURS = ("", "MAJ", "CTRL", "ALT")

# Les quatre directions du mode "touches", dans l'ordre ou la page web et
# profiles.py les presentent.
DIRECTIONS = ("gauche", "droite", "haut", "bas")


def reglage(nom, defaut):
    """Lit un reglage de config.py, avec un repli s'il est ancien.

    Meme detour que dans main.py, et pour la meme raison : le projet te dit
    de GARDER ton config.py quand tu televerses une nouvelle version du
    dossier device. Un firmware neuf tourne donc tres souvent avec un
    config.py qui ne connait pas encore les constantes du joystick.
    """
    return getattr(C, nom, defaut)


def fraction(brut, centre, zone_morte, inverse=False):
    """Position brute d'un axe -> fraction de -1.0 a +1.0. 0.0 au repos.

    TROIS CHOSES SE PASSENT ICI, ET AUCUNE N'EST SUPERFLUE.

    1. ON NORMALISE CHAQUE COTE SEPAREMENT. Si le centre mesure 30000, il
       reste 35535 de course vers le haut et seulement 30000 vers le bas.
       Diviser les deux par la meme valeur rendrait le stick plus rapide
       dans un sens que dans l'autre - defaut tres desagreable, et tres
       difficile a comprendre quand on ne sait pas d'ou il vient.

    2. ON RETIRE LA ZONE MORTE. En dessous, on rend 0.0 : un stick au repos
       ne doit pas faire deriver la vue tout seul.

    3. ON RE-ETALE CE QUI RESTE. Sans cela, le mouvement SAUTERAIT a la
       sortie de la zone morte : avec une zone morte de 12 %, le premier
       deplacement vaudrait deja 12 % de la vitesse maximale. On remet donc
       l'intervalle restant a l'echelle, et le mouvement demarre a zero.
    """
    try:
        brut = int(brut)
        centre = int(centre)
    except (TypeError, ValueError):
        return 0.0
    if centre <= 0 or centre >= PLEINE_ECHELLE:
        # Un centre a 0 ou au maximum veut dire que l'etalonnage s'est fait
        # stick pousse a fond, ou que la broche ne lit rien. Dans les deux
        # cas on ne peut rien calculer de fiable : on rend 0.0 plutot qu'un
        # mouvement invente.
        return 0.0

    ecart = brut - centre
    if ecart >= 0:
        f = ecart / float(PLEINE_ECHELLE - centre)
    else:
        f = ecart / float(centre)
    if f > 1.0:
        f = 1.0
    elif f < -1.0:
        f = -1.0

    zone = _zone(zone_morte)
    if -zone <= f <= zone:
        return 0.0
    if f > 0:
        f = (f - zone) / (1.0 - zone)
    else:
        f = (f + zone) / (1.0 - zone)
    return -f if inverse else f


def _zone(pourcentage):
    """La zone morte en fraction de la course, bornee pour rester utile.

    En dessous de 1 %, un stick de qualite moyenne derive tout seul. Au-dela
    de 60 %, il ne resterait presque plus de course utile. On borne donc, au
    lieu de refuser : un reglage absurde doit degrader le confort, pas
    empecher le joystick de fonctionner.
    """
    try:
        valeur = float(pourcentage)
    except (TypeError, ValueError):
        valeur = 12.0
    if valeur < 1.0:
        valeur = 1.0
    elif valeur > 60.0:
        valeur = 60.0
    return valeur / 100.0


def deplacement(f, sensibilite):
    """Fraction -> nombre de pas a envoyer, BORNE.

    LE BORNAGE N'EST PAS UNE PRECAUTION DECORATIVE. La bibliotheque souris
    officielle leve ValueError des qu'un axe sort de -127..127, et son
    empaquetage (struct "Bbb") leverait de toute facon. Une sensibilite mal
    reglee ferait donc tomber la boucle principale, c'est-a-dire tout le
    macropad : plus d'ecran, plus de LED, plus de bouton ESC.
    """
    try:
        sensibilite = float(sensibilite)
    except (TypeError, ValueError):
        sensibilite = 6.0
    if sensibilite < 0:
        sensibilite = 0.0
    pas = int(round(f * sensibilite))
    if pas > DEPLACEMENT_MAX:
        return DEPLACEMENT_MAX
    if pas < -DEPLACEMENT_MAX:
        return -DEPLACEMENT_MAX
    return pas


def direction(fx, fy):
    """La direction dominante, pour le mode "touches". None si au repos.

    Le mode "touches" n'envoie pas un deplacement mais un raccourci - par
    exemple le pave numerique 4 ou 6 de Blender, qui tournent la vue par
    pas de 15 degres. Un raccourci n'a pas de nuance : il faut choisir UNE
    direction, et c'est la plus franche qui gagne.
    """
    if not fx and not fy:
        return None
    if abs(fx) >= abs(fy):
        return "droite" if fx > 0 else "gauche"
    # Attention au sens : sur un ecran, l'axe Y descend. Pousser le stick
    # vers l'avant doit donner "haut", et c'est au reglage inverser_y de
    # corriger si ton module est monte dans l'autre sens.
    return "bas" if fy > 0 else "haut"


def reglages_valides(brut):
    """Nettoie un bloc de reglages venant d'un profil. Ne leve jamais.

    Un profils.json peut avoir ete edite a la main, ecrit par une version
    plus ancienne, ou tronque. La regle du projet est constante : on repare
    en silence vers une valeur sure, on ne refuse pas, et surtout on ne
    laisse pas une valeur folle arriver jusqu'a l'USB.
    """
    if not isinstance(brut, dict):
        brut = {}
    mode = str(brut.get("mode", MODE_ETEINT)).strip().lower()
    if mode not in MODES:
        mode = MODE_ETEINT
    modif = str(brut.get("modificateur", "")).strip().upper()
    if modif in ("SHIFT",):
        modif = "MAJ"
    if modif not in MODIFICATEURS:
        modif = ""
    try:
        sens = int(brut.get("sensibilite", 6))
    except (TypeError, ValueError):
        sens = 6
    if sens < 1:
        sens = 1
    elif sens > 15:
        sens = 15
    try:
        zone = int(brut.get("zone_morte", 12))
    except (TypeError, ValueError):
        zone = 12
    if zone < 1:
        zone = 1
    elif zone > 60:
        zone = 60
    return {
        "mode": mode,
        "modificateur": modif,
        "sensibilite": sens,
        "zone_morte": zone,
        "inverser_x": bool(brut.get("inverser_x", False)),
        "inverser_y": bool(brut.get("inverser_y", False)),
    }


class Joystick:
    """Ce que le stick demande, sans jamais savoir comment on l'executera."""

    def __init__(self):
        self.centre_x = None        # None = pas encore etalonne
        self.centre_y = None
        self.etat = REPOS
        self.reglages = reglages_valides(None)
        self._rentre = None         # instant du retour au repos, ou None
        self._prochain = 0          # avant cet instant, on n'envoie rien
        self._aveugle = 0           # instant jusqu'auquel on ignore les axes
        # VERROU APRES UNE INTERRUPTION. Quand ESC referme une orbite, le
        # stick est encore pousse : sans ce verrou, le tour de boucle
        # SUIVANT en recommencerait aussitot une nouvelle, et ESC n'aurait
        # eu aucun effet visible. Il faut ramener le stick au repos pour
        # repartir - c'est ce qu'on attend d'une touche d'annulation.
        self._bloque = False
        self.derniere = (0.0, 0.0)  # pour l'ecran et les diagnostics

    # ------------------------------------------------------------------
    # Etalonnage
    # ------------------------------------------------------------------
    def etalonner(self, lectures):
        """Memorise le centre a partir de plusieurs lectures AU REPOS.

        Retourne True si l'etalonnage est credible. Il echoue - et c'est
        voulu - si le stick bougeait pendant la mesure : un centre pris
        stick pousse rendrait la vue folle, et personne ne comprendrait
        pourquoi. Mieux vaut un joystick qui refuse de demarrer qu'un
        joystick qui derive.
        """
        xs, ys = [], []
        for lecture in lectures or ():
            try:
                x, y = lecture
                xs.append(int(x))
                ys.append(int(y))
            except (TypeError, ValueError):
                continue
        if len(xs) < 3:
            return False
        # Une dispersion large pendant la mesure veut dire que le stick
        # n'etait pas au repos. 4 % de la pleine echelle laisse passer le
        # bruit normal du convertisseur et arrete une main sur le stick.
        marge = PLEINE_ECHELLE * 4 // 100
        if (max(xs) - min(xs)) > marge or (max(ys) - min(ys)) > marge:
            return False
        self.centre_x = sum(xs) // len(xs)
        self.centre_y = sum(ys) // len(ys)
        return self.etalonne()

    def etalonne(self):
        """A-t-on un centre exploitable ?"""
        for centre in (self.centre_x, self.centre_y):
            if centre is None or centre <= 0 or centre >= PLEINE_ECHELLE:
                return False
        return True

    # ------------------------------------------------------------------
    # Reglages
    # ------------------------------------------------------------------
    def regler(self, brut):
        """Applique les reglages du profil actif.

        Appele a chaque changement de profil, y compris quand le PC le
        change tout seul selon la fenetre active. Un glissement en cours est
        ABANDONNE : les reglages d'un logiciel ne doivent pas finir un
        mouvement commence dans un autre.

        Une premiere version se contentait de REPONDRE qu'un glissement
        etait en cours, sans l'abandonner. main.py relachait donc le bouton
        du milieu, mais la machine a etats restait en GLISSE : les tours
        suivants continuaient d'envoyer du mouvement avec un bouton
        relache, et la vue se baladait sans tourner.
        """
        self.reglages = reglages_valides(brut)
        return self.abandonner()

    def mode(self):
        return self.reglages["mode"]

    def modificateur(self):
        return self.reglages["modificateur"]

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------
    def fractions(self, x, y):
        """Les deux axes, zone morte et inversion appliquees."""
        zone = self.reglages["zone_morte"]
        fx = fraction(x, self.centre_x, zone, self.reglages["inverser_x"])
        fy = fraction(y, self.centre_y, zone, self.reglages["inverser_y"])
        self.derniere = (fx, fy)
        return fx, fy

    def ignorer(self, now=None, duree=None):
        """Ferme les yeux sur les axes pendant un court instant.

        A QUOI CA SERT : sur un module a quelques euros, le clic du stick
        est dur et decentre. En enfoncant, on BOUGE le stick. Comme ce clic
        est devenu la touche B1, chaque appui enverrait un petit mouvement
        parasite a la vue 3D.

        Pendant cet aveuglement, un glissement en cours n'est NI poursuivi
        NI termine : le chronometre du retour au repos est gele. Un clic au
        milieu d'une orbite ne la coupe donc pas.
        """
        now = ticks_ms() if now is None else now
        if duree is None:
            duree = reglage("JOYSTICK_CLIC_AVEUGLE_MS", 80)
        self._aveugle = ticks_add(now, int(duree))

    def service(self, x, y, now=None):
        """Le coeur. Retourne (action, dx, dy) a chaque tour de boucle.

        Appele environ 500 fois par seconde, et c'est volontaire : lire les
        axes est tres rapide. Ce qui est limite, c'est l'ENVOI - l'USB ne
        transporte qu'environ 125 rapports par seconde - et c'est la cadence
        qui s'en occupe.
        """
        now = ticks_ms() if now is None else now

        # Eteint, ou pas etalonne : on ne fait rien, mais on n'oublie pas de
        # refermer un glissement qui serait reste ouvert.
        if self.mode() == MODE_ETEINT or not self.etalonne():
            if self.etat != REPOS:
                return self._terminer()
            return (RIEN, 0, 0)

        if ticks_diff(now, self._aveugle) < 0:
            self._rentre = None        # on gele le retour au repos
            return (RIEN, 0, 0)

        fx, fy = self.fractions(x, y)
        actif = bool(fx) or bool(fy)

        if self.etat == REPOS:
            if not actif:
                self._bloque = False       # le stick est revenu au milieu
                return (RIEN, 0, 0)
            if self._bloque:
                # On a ete interrompu et le stick n'est pas encore revenu
                # au repos : on ne repart pas tout seul.
                return (RIEN, 0, 0)
            self.etat = GLISSE
            self._rentre = None
            # On attend une cadence avant le premier deplacement : Windows
            # doit voir le bouton s'enfoncer AVANT de voir bouger, sinon le
            # logiciel 3D prend le mouvement pour un simple survol.
            self._prochain = ticks_add(now, self._cadence())
            return (COMMENCER, 0, 0)

        # --- un glissement est en cours ---
        if actif:
            self._rentre = None
            if ticks_diff(now, self._prochain) < 0:
                return (RIEN, 0, 0)
            self._prochain = ticks_add(now, self._cadence())
            sens = self.reglages["sensibilite"]
            dx = deplacement(fx, sens)
            dy = deplacement(fy, sens)
            if not dx and not dy:
                # Arrondi a zero : inutile d'occuper l'USB pour ne rien dire.
                return (RIEN, 0, 0)
            return (BOUGER, dx, dy)

        # Le stick est revenu au repos. On ne termine pas tout de suite :
        # voir "LE PIEGE DU RETOUR AU CENTRE" en tete de fichier.
        if self._rentre is None:
            self._rentre = now
        if ticks_diff(now, self._rentre) >= reglage("JOYSTICK_FIN_MS", 120):
            return self._terminer()
        return (RIEN, 0, 0)

    def abandonner(self):
        """Oublie un glissement en cours. True s'il faut encore relacher.

        Appele au changement de profil, a l'appui sur ESC, et dans le
        finally de la boucle principale. UN BOUTON DU MILIEU RESTE ENFONCE
        COTE WINDOWS EST PIRE QU'UN CTRL : la vue tourne sans fin et il faut
        aller cliquer pour s'en sortir.
        """
        if self.etat == REPOS:
            return False
        self.etat = REPOS
        self._rentre = None
        self._bloque = True
        return True

    def _terminer(self):
        self.etat = REPOS
        self._rentre = None
        return (TERMINER, 0, 0)

    def _cadence(self):
        if self.mode() == MODE_TOUCHES:
            # UN RACCOURCI NE SE REPETE PAS QUATRE-VINGTS FOIS PAR SECONDE.
            # En mode "touches" on n'envoie pas un deplacement mais une
            # frappe - le pave numerique 4 de Blender, par exemple. A la
            # cadence de la souris, une seconde d'inclinaison enverrait
            # quatre-vingts rotations de 15 degres : la vue partirait en
            # vrille. On vise donc le rythme d'une touche maintenue.
            return int(reglage("JOYSTICK_TOUCHES_MS", 180))
        valeur = int(reglage("JOYSTICK_CADENCE_MS", 12))
        # En dessous de 8 ms on depasse ce que l'interface accepte
        # (interval_ms=8 par defaut dans la bibliotheque) : les rapports
        # seraient simplement perdus, ce qui donnerait un mouvement saccade
        # sans que rien ne le signale.
        return valeur if valeur >= 8 else 8
