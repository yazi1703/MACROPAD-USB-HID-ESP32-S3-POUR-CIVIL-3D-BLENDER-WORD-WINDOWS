# -*- coding: utf-8 -*-
"""
rgb.py - Les LED RGB sous les touches.

=====================================================================
CE QUE CA FAIT
=====================================================================
* chaque profil a sa couleur : d'un coup d'oeil, tu sais si le macropad
  est en CIVIL 3D ou en BLENDER, sans lire l'ecran. Comme le PC dit au
  macropad quel logiciel est au premier plan, la couleur suit le logiciel
  tout seul : tu cliques dans Civil 3D, le pad devient bleu ;
* la couleur RESPIRE doucement, comme la LED du bouton ESC : elle monte
  et redescend sur RGB_RESPIRATION_MS. Une couleur fixe se remarque une
  fois puis s'oublie ; une couleur qui respire reste vivante sans jamais
  clignoter ni attirer l'oeil au mauvais moment ;
* la touche sur laquelle tu appuies S'INTENSIFIE aussitot, puis revient
  a la couleur du profil en douceur. Deux appuis coup sur coup montent
  deux fois plus haut : l'impulsion s'ajoute a ce qui reste de la
  precedente, au lieu de la remplacer. La LED reagit au DOIGT, sur le
  front d'appui, sans attendre de savoir quelle macro partira ;
* apres RGB_VEILLE_MS sans rien toucher, tout s'eteint - pour les yeux,
  pour la duree de vie des LED, et surtout pour le courant.

=====================================================================
DEUX MONTAGES POSSIBLES, ET UN SEUL FIL DE CODE POUR LES DEUX
=====================================================================
RGB_TYPE = "WS2812"   LED adressables (NeoPixel, SK6812...). UN seul fil
                      de donnees pour toute la guirlande, et une couleur
                      DIFFERENTE par touche. C'est ce qu'il faut pour
                      eclairer six touches.

RGB_TYPE = "PWM"      UNE LED RGB ordinaire a quatre pattes, sur trois
                      broches. Une seule couleur pour tout le macropad :
                      la couleur du profil. Pas de couleur par touche -
                      il faudrait trois broches PAR touche, soit dix-huit.

Livre avec RGB_ENABLED = False : rien ne bouge tant que tu n'as pas
cable et choisi ton type.

=====================================================================
CE QUI RISQUE DE CRAMER, OU DE FAIRE REDEMARRER LA CARTE
=====================================================================
1. LE COURANT, C'EST LE VRAI DANGER. Une WS2812 en blanc a fond tire
   60 mA. Six touches = 360 mA, plus la carte, plus l'ecran : on depasse
   les 500 mA que fournit un port USB ordinaire. Le 5 V s'effondre, la
   carte redemarre, et ton clavier disparait en pleine frappe.

   La parade est dans le code : RGB_LUMINOSITE plafonne CHAQUE canal
   avant l'envoi. A la valeur livree (40 sur 255), six LED tirent environ
   60 mA au total. Ne monte pas ce chiffre sans mesurer.

2. LES WS2812 SE NOURRISSENT EN 5 V, PAS EN 3,3 V. Le regulateur 3,3 V
   de la carte n'a pas la marge ; il faut prendre le 5 V (VBUS).

3. LE FIL DE DONNEES SORT EN 3,3 V. Une WS2812 alimentee en 5 V attend
   un niveau haut d'au moins 3,5 V : on est JUSTE en dessous. Souvent ca
   passe, parfois non - et quand ca ne passe pas, les couleurs sautent au
   hasard. Deux remedes eprouves :
     * une resistance de 220 a 470 ohms EN SERIE sur le fil de donnees,
       au plus pres de la premiere LED (elle protege aussi le GPIO). Sa
       valeur exacte n'a aucune importance : elle amortit le signal, elle
       ne fixe aucun courant ;
     * si ca scintille encore, alimente la guirlande en ~4,3 V en
       intercalant une diode 1N4148 entre le 5 V et son VCC : le seuil
       descend a 3,0 V et le probleme disparait.

4. UN CONDENSATEUR DE 470 uF entre 5 V et GND, au plus pres des LED.
   Elles commutent tres vite et tirent des pointes de courant ; sans
   reservoir local, ces pointes se voient sur toute l'alimentation.
   100 uF suffisent pour six LED ; les valeurs de 1000 uF qu'on lit
   partout visent des rubans de cinquante ou cent LED. ATTENTION A LA
   POLARITE : un chimique monte a l'envers gonfle et explose.

5. NE JAMAIS brancher le fil de donnees sur une LED deja alimentee alors
   que la carte est hors tension : le courant passerait par la diode de
   protection du GPIO. Alimente les deux ensemble.
"""

from math import cos, pi
from time import ticks_ms, ticks_diff, ticks_add
import config as C

def respiration(phase_ms):
    """Facteur de luminosite (0.0 a 1.0) a un instant du cycle.

    C'est exactement la courbe de la LED du bouton ESC (voir led.py) :
    (1 - cos) / 2 part de zero, monte en douceur, redescend en douceur.
    L'exposant 1.6 fait s'attarder la couleur dans les valeurs basses et
    ne fait que passer par le maximum - c'est ce qui donne une
    respiration plutot qu'un clignotement.

    LE PLAFOND N'EST PAS 1.0, ET C'EST VOLONTAIRE. Au repos la couleur
    monte au plus a RGB_RESPIRATION_MAX, ce qui laisse de la place
    au-dessus pour l'appui. Sans cette reserve, une couleur dont un canal
    vaut 255 - le bleu de CIVIL3D, par exemple - touchait deja le plafond
    de courant au sommet du cycle : l'appui ne pouvait plus l'eclaircir,
    il ne faisait que DELAVER les autres canaux. Sur un bleu pur, il
    n'aurait rien fait du tout.

    Fonction pure : elle ne depend que de son argument, donc elle se teste
    sans la moindre LED.
    """
    periode = getattr(C, "RGB_RESPIRATION_MS", 4000)
    plancher = getattr(C, "RGB_RESPIRATION_MIN", 0.25)
    plafond = getattr(C, "RGB_RESPIRATION_MAX", 0.55)
    onde = (1 - cos(2 * pi * (phase_ms % periode) / periode)) / 2
    return plancher + (plafond - plancher) * onde ** 1.6


class Rgb:
    """Pilote les LED RGB. Se desactive toute seule en cas de probleme."""

    def __init__(self):
        self.actif = False
        self.materiel = None
        self.type = None
        self.nb = 0
        self.base = (0, 0, 0)          # couleur du profil courant
        self._erreur = False           # panne HID : tout passe au rouge
        # Une "energie" par touche : elle monte a chaque appui et redescend
        # toute seule. C'est ce qui fait qu'un appui se voit tout de suite
        # et que deux appuis montent deux fois plus haut.
        self.niveaux = [0.0] * max(int(getattr(C, "RGB_COUNT", 6)), 1)
        self._activite = ticks_ms()
        self._eteint = False
        self._a_redessiner = True
        self._prochain = 0
        self._phase = 0            # ou on en est dans la respiration
        self._dernier = ticks_ms()
        if not getattr(C, "RGB_ENABLED", False):
            # On le DIT. Un ruban qui reste noir sans un mot dans le REPL
            # envoie chercher la panne dans le cablage alors que le
            # firmware n'a simplement jamais eu l'ordre de l'allumer.
            # C'est le meme piege que HID_ENABLED : reteleverser le
            # dossier device ecrase config.py et remet les deux a False.
            print("RGB : desactive (RGB_ENABLED = False dans config.py)")
            return
        try:
            self._demarrer()
            self.actif = True
            print("RGB : %d LED sur GPIO%s, ordre %s, luminosite %d/255"
                  % (self.nb,
                     getattr(C, "RGB_PIN", "?") if self.type == "WS2812"
                     else "%s/%s/%s" % (C.RGB_PIN_R, C.RGB_PIN_V, C.RGB_PIN_B),
                     getattr(C, "RGB_ORDRE", "GRB"),
                     getattr(C, "RGB_LUMINOSITE", 40)))
        except Exception as exc:
            # Une LED absente ou mal cablee ne doit JAMAIS empecher le
            # macropad de taper. Meme regle que pour l'ecran.
            print("RGB desactive :", exc)

    # ------------------------------------------------------------------
    def _demarrer(self):
        from machine import Pin
        self.type = getattr(C, "RGB_TYPE", "WS2812")
        if self.type == "WS2812":
            from neopixel import NeoPixel
            self.nb = int(getattr(C, "RGB_COUNT", 6))
            self.materiel = NeoPixel(Pin(C.RGB_PIN, Pin.OUT), self.nb)
        elif self.type == "PWM":
            from machine import PWM
            self.nb = 1
            self.materiel = tuple(
                PWM(Pin(broche, Pin.OUT), freq=1000, duty_u16=0)
                for broche in (C.RGB_PIN_R, C.RGB_PIN_V, C.RGB_PIN_B))
        else:
            raise ValueError("RGB_TYPE inconnu : " + str(self.type))

    def desactiver(self, exc):
        print("RGB desactive :", exc)
        self.actif = False

    # ------------------------------------------------------------------
    # Ce que main.py appelle
    # ------------------------------------------------------------------
    def profil(self, couleur):
        """Nouvelle couleur de fond : celle du logiciel qui vient d'etre pris.

        C'est main.py qui choisit la couleur, a partir de la configuration :
        rgb.py ne connait pas les noms de profils, seulement des couleurs.
        """
        self.base = tuple(couleur or C.RGB_COULEUR_DEFAUT)
        for index in range(len(self.niveaux)):
            self.niveaux[index] = 0.0
        self._a_redessiner = True
        self.reveiller(ticks_ms())

    def etat(self, texte):
        """Le bandeau de l'ecran change : on en profite pour signaler.

        ERR est le seul cas ou la couleur du profil s'efface : quand le
        clavier est en panne, tu dois le voir sans lire l'ecran.
        """
        erreur = (texte == "ERR")
        if erreur != self._erreur:
            self._erreur = erreur
            self._a_redessiner = True

    def touche(self, index, now):
        """Un appui vient d'avoir lieu : la LED de cette touche s'intensifie.

        On AJOUTE l'impulsion a ce qui reste de la precedente, plafonnee :
        deux appuis rapides montent deux fois plus haut, dix appuis ne
        montent pas dix fois plus haut. Le plafond du courant, lui, reste
        celui de limiter() - personne ne peut faire redemarrer la carte a
        force d'appuyer.
        """
        self.reveiller(now)
        if 0 <= index < len(self.niveaux):
            plafond = getattr(C, "RGB_IMPULSION_MAX", 3.0)
            niveau = self.niveaux[index] + getattr(C, "RGB_IMPULSION", 1.0)
            self.niveaux[index] = plafond if niveau > plafond else niveau
            self._a_redessiner = True

    def reveiller(self, now):
        self._activite = now
        if self._eteint:
            self._eteint = False
            self._a_redessiner = True

    # ------------------------------------------------------------------
    def tick(self, now):
        """A appeler a chaque tour de boucle. N'attend jamais."""
        if not self.actif:
            return

        if (not self._eteint
                and ticks_diff(now, self._activite) > C.RGB_VEILLE_MS):
            self._eteint = True
            self._a_redessiner = True

        # La respiration avance avec le TEMPS ECOULE, pas avec le nombre de
        # tours de boucle : le rythme reste le meme quoi que fasse le
        # macropad par ailleurs.
        ecoule = ticks_diff(now, self._dernier)
        self._dernier = now
        if not (0 < ecoule < 1000):
            ecoule = 0                 # un saut d'horloge ne fait rien sauter
        if getattr(C, "RGB_RESPIRATION", True) and not self._eteint:
            self._phase += ecoule
            self._a_redessiner = True

        # Les impulsions redescendent toutes seules, proportionnellement au
        # temps ecoule : la retombee dure RGB_RETOMBEE_MS par unite, quelle
        # que soit la vitesse de la boucle.
        if ecoule:
            perte = float(ecoule) / getattr(C, "RGB_RETOMBEE_MS", 700)
            for index in range(len(self.niveaux)):
                if self.niveaux[index] > 0:
                    reste = self.niveaux[index] - perte
                    self.niveaux[index] = reste if reste > 0 else 0.0
                    self._a_redessiner = True

        if not self._a_redessiner or ticks_diff(now, self._prochain) < 0:
            return
        self._prochain = ticks_add(now, C.RGB_MS)
        self._a_redessiner = False
        try:
            self._envoyer()
        except Exception as exc:
            self.desactiver(exc)

    def _envoyer(self):
        if self._eteint:
            self._peindre_tout((0, 0, 0))
            return
        fond = tuple(C.RGB_COULEUR_ERREUR) if self._erreur else self.base
        # Le souffle de la respiration, entre son plancher et 1.0. Les
        # impulsions des touches s'AJOUTENT par-dessus : un appui monte
        # donc pareil, que la respiration soit en haut ou en bas de son
        # cycle. C'est ce qu'on attend d'un retour visuel.
        # Le niveau de REPOS, respiration ou pas. Il ne vaut jamais 1.0 :
        # tout ce qui reste au-dessus appartient a l'appui. Une couleur
        # figee a 1.0 rendrait exactement le defaut d'origine - la touche
        # appuyee ne se distinguerait plus des autres.
        souffle = getattr(C, "RGB_RESPIRATION_MAX", 0.55)
        if getattr(C, "RGB_RESPIRATION", True):
            souffle = respiration(self._phase)

        if self.type == "PWM":
            # Une seule LED pour tout le pad : elle prend l'impulsion la
            # plus forte du moment.
            plus_haut = 0.0
            for niveau in self.niveaux:
                if niveau > plus_haut:
                    plus_haut = niveau
            self._peindre_tout(_attenuer(fond, souffle + plus_haut))
            return

        for index in range(self.nb):
            niveau = self.niveaux[index] if index < len(self.niveaux) else 0.0
            self._pixel(index, _attenuer(fond, souffle + niveau))
        self.materiel.write()

    def _peindre_tout(self, couleur):
        if self.type == "PWM":
            self._pwm(couleur)
            return
        for index in range(self.nb):
            self._pixel(index, couleur)
        self.materiel.write()

    # ------------------------------------------------------------------
    # Bas niveau
    # ------------------------------------------------------------------
    def _pixel(self, index, couleur):
        r, v, b = limiter(couleur)
        # Les WS2812 attendent l'ordre VERT, ROUGE, BLEU. C'est la cause
        # n°1 des "mes rouges sortent verts" : si tes couleurs sont
        # permutees, c'est RGB_ORDRE qu'il faut changer, pas ton cablage.
        ordre = getattr(C, "RGB_ORDRE", "GRB")
        valeurs = {"R": r, "G": v, "B": b}
        self.materiel[index] = tuple(valeurs[lettre] for lettre in ordre)

    def _pwm(self, couleur):
        valeurs = limiter(couleur)
        for canal, valeur in zip(self.materiel, valeurs):
            rapport = valeur * 257            # 0..255 -> 0..65535
            if getattr(C, "RGB_ANODE_COMMUNE", True):
                # Anode commune : la patte commune est au +, le GPIO tire
                # vers le bas. Zero volt = allume, d'ou l'inversion.
                rapport = 65535 - rapport
            canal.duty_u16(rapport)

    def close(self):
        """Tout eteindre en partant. Une LED oubliee allumee, ca se voit."""
        if not self.actif:
            return
        try:
            self._peindre_tout((0, 0, 0))
        except Exception:
            pass
        self.actif = False


def _attenuer(couleur, facteur):
    """Multiplie une couleur par un facteur de 0.0 a 1.0."""
    return tuple(int(valeur * facteur) for valeur in couleur)


def limiter(couleur):
    """Plafonne la couleur a RGB_LUMINOSITE. C'EST LA SECURITE COURANT.

    Elle est ici, dans le code, et pas laissee au bon vouloir de celui qui
    choisit les couleurs : personne ne peut demander du blanc a fond sur
    six LED et faire redemarrer la carte en pleine frappe.
    """
    plafond = getattr(C, "RGB_LUMINOSITE", 40)
    sortie = []
    for valeur in couleur:
        valeur = int(valeur)
        if valeur < 0:
            valeur = 0
        elif valeur > 255:
            valeur = 255
        sortie.append(valeur * plafond // 255)
    return tuple(sortie)
