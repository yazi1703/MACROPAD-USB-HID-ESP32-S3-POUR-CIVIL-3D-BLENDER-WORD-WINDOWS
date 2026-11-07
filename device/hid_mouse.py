# -*- coding: utf-8 -*-
"""
hid_mouse.py - La souris USB, et la raison pour laquelle on la reecrit.

=====================================================================
POURQUOI CE FICHIER EXISTE
=====================================================================
La bibliotheque officielle de MicroPython fournit bien une souris :
device/lib/usb/device/mouse.py, recopiee telle quelle (licence MIT,
auteur Angus Gratton). Mais on ne peut pas l'utiliser directement, et la
raison est grave.

Sa methode send_report() contient ceci, mot pour mot :

    while self.busy():
        machine.idle()

AUCUNE LIMITE DE TEMPS. Tant que l'hote n'a pas vide le precedent
rapport, cette boucle tourne. Si le PC se met en veille, si le cable est
arrache, si le pilote tousse, elle ne rend JAMAIS la main.

Or tout le macropad vit dans une seule boucle cooperative. Un appel qui
ne rend pas la main, c'est l'ecran fige, les LED figees, et surtout
LE BOUTON ESC INOPERANT. On aurait echange un joystick contre la touche
d'annulation : tres mauvaise affaire au milieu d'un dessin.

La classe parente, elle, fait les choses correctement :

    HIDInterface.send_report(self, report_data, timeout_ms=100)

Elle calcule une echeance et rend False quand elle est depassee. La
sous-classe souris MASQUE cette methode et perd la protection au passage.

On reecrit donc l'envoi en passant par le parent avec timeout_ms=0, ce
qui est exactement ce que fait hid_keyboard.py depuis le debut. Et le
commentaire d'origine de la bibliotheque dit lui-meme que cette boucle
d'attente peut etre retiree si l'on accepte de perdre un rapport de temps
en temps - ce qui est precisement notre cas.

=====================================================================
POURQUOI PERDRE UN RAPPORT N'EST PAS GRAVE (MAIS PERDRE UN CLIC, OUI)
=====================================================================
Un rapport de souris transporte deux choses tres differentes :

  LE DEPLACEMENT est RELATIF : "avance de 7 pixels". S'il est perdu, le
  suivant arrive 12 ms plus tard. On ACCUMULE donc le deplacement non
  envoye, et rien n'est reellement perdu, juste retarde d'un cheveu.

  L'ETAT DES BOUTONS est ABSOLU : "le bouton du milieu est enfonce". S'il
  est perdu, Windows reste sur son idee precedente - et un bouton du
  milieu reste enfonce fait tourner la vue 3D sans fin. On REPETE donc
  l'etat voulu a chaque tour jusqu'a ce qu'il parte vraiment.

C'est pour ca que ce fichier distingue "ce que je veux" de "ce que
Windows croit". Les deux ne sont pas toujours d'accord, et c'est normal.

=====================================================================
VOCABULAIRE DES VARIABLES
=====================================================================
  _voulu_milieu  etat du bouton du milieu que NOUS voulons
  _etat_milieu   etat que Windows croit, d'apres le dernier envoi reussi
  _dx, _dy       deplacement accumule, pas encore envoye
  opened         Windows a-t-il configure la souris ?
  fault          une panne grave est survenue, on n'envoie plus rien
"""

from time import ticks_ms, ticks_diff, sleep_ms

# Le bornage vit dans joystick.py parce que c'est la que la valeur est
# calculee, et qu'on veut la verifier sans materiel. Ici on s'en sert comme
# d'un dernier filet : deux remparts valent mieux qu'un quand l'alternative
# est une exception au milieu de la boucle principale.
from joystick import DEPLACEMENT_MAX


def _borne(valeur):
    if valeur > DEPLACEMENT_MAX:
        return DEPLACEMENT_MAX
    if valeur < -DEPLACEMENT_MAX:
        return -DEPLACEMENT_MAX
    return int(valeur)


class HIDMouse:
    """Le pilote souris. N'attend jamais, et relache toujours."""

    def __init__(self, interface):
        self.interface = interface
        self.opened = False
        self.fault = False
        self._voulu_milieu = False
        self._etat_milieu = False
        self._dx = 0
        self._dy = 0
        self._perdus = 0          # rapports refuses d'affilee, pour le log
        self._prevenu = False

    # ------------------------------------------------------------------
    # Etats
    # ------------------------------------------------------------------
    def ready(self):
        """Peut-on envoyer quelque chose a cet instant ?"""
        return self.opened and not self.fault

    def enfonce(self):
        """Le bouton du milieu est-il enfonce cote Windows ?"""
        return self._etat_milieu

    def en_attente(self):
        """Reste-t-il quelque chose a envoyer ?"""
        return (self._voulu_milieu != self._etat_milieu
                or bool(self._dx) or bool(self._dy))

    # ------------------------------------------------------------------
    # Demandes venant de main.py
    # ------------------------------------------------------------------
    def milieu(self, enfonce):
        """Demande l'etat du bouton du milieu. Rien n'est envoye ici."""
        self._voulu_milieu = bool(enfonce)

    def bouger(self, dx, dy):
        """Ajoute un deplacement a envoyer. Rien n'est envoye ici.

        On ACCUMULE au lieu de remplacer : si le rapport precedent n'est pas
        encore parti, les deux mouvements s'additionnent et le geste reste
        fidele a ce que fait la main.
        """
        self._dx += int(dx)
        self._dy += int(dy)
        # On borne l'accumulation elle-meme. Sans cela, un joystick pousse a
        # fond pendant que l'USB est bouche creerait une reserve de plusieurs
        # milliers de pixels, qui partirait d'un coup au rebranchement : la
        # vue ferait un saut spectaculaire et incomprehensible.
        reserve = DEPLACEMENT_MAX * 2
        if self._dx > reserve:
            self._dx = reserve
        elif self._dx < -reserve:
            self._dx = -reserve
        if self._dy > reserve:
            self._dy = reserve
        elif self._dy < -reserve:
            self._dy = -reserve

    def tout_relacher(self):
        """Annule le deplacement en attente et demande le relachement.

        Appele au changement de profil, sur ESC, et quand le joystick
        abandonne un glissement. Le deplacement en attente est jete : il
        appartenait au geste qu'on vient d'interrompre.
        """
        self._dx = 0
        self._dy = 0
        self._voulu_milieu = False

    # ------------------------------------------------------------------
    # Envoi
    # ------------------------------------------------------------------
    def tick(self, now=None):
        """Envoie AU PLUS un rapport, et rend la main. Jamais bloquant.

        Un seul rapport porte a la fois l'etat du bouton et le deplacement :
        c'est le format USB d'une souris, et c'est aussi ce qui garantit que
        le bouton s'enfonce AVANT que le mouvement ne commence, sans avoir a
        synchroniser deux envois.
        """
        now = ticks_ms() if now is None else now
        try:
            ouvert = self.interface.is_open()
        except Exception as exc:
            self._panne("etat de l'interface illisible", exc)
            return

        if not ouvert:
            # Debranchement, veille, ou reinitialisation du port. Windows a
            # de toute facon oublie l'etat des boutons : on repart de zero
            # plutot que de croire qu'un bouton est encore enfonce.
            #
            # ON OUBLIE AUSSI CE QU'ON VOULAIT, et c'est la meme regle que
            # pour le clavier, qui jette sa file de macros au
            # debranchement : HORS DE QUESTION QU'UN CLIC PARTE TOUT SEUL
            # AU REBRANCHEMENT. Un bouton du milieu qui s'enfonce sans
            # qu'on ait rien demande, dans le logiciel qui a le focus a ce
            # moment-la, est exactement le genre de surprise qu'on refuse.
            if self.opened:
                print("Souris : deconnexion/reset USB, glissement oublie")
            self.opened = False
            self._etat_milieu = False
            self._voulu_milieu = False
            self._dx = 0
            self._dy = 0
            return

        if not self.opened:
            print("Souris : interface ouverte par Windows")
            self.opened = True
            # Un hote qui vient de reconfigurer le peripherique a tout
            # oublie : un incident passe ne doit pas exiger un RESET.
            self.fault = False
            self._etat_milieu = False

        if self.fault or not self.en_attente():
            return

        dx = _borne(self._dx)
        dy = _borne(self._dy)
        try:
            envoye = self.interface.rapport(self._voulu_milieu, dx, dy)
        except Exception as exc:
            self._panne("envoi impossible", exc)
            return

        if not envoye:
            # L'USB est occupe. On ne retire RIEN de l'accumulation et on
            # reessaiera au prochain tour, dans deux millisecondes.
            self._perdus += 1
            if self._perdus == 50 and not self._prevenu:
                self._prevenu = True
                print("Souris : l'USB refuse les rapports depuis 100 ms")
            return

        self._perdus = 0
        self._etat_milieu = self._voulu_milieu
        self._dx -= dx
        self._dy -= dy

    def _panne(self, quoi, exc):
        if not self.fault:
            print("Souris : %s (%s)" % (quoi, exc))
            print("Souris : desactivee. Le clavier continue de fonctionner.")
        self.fault = True
        self._dx = 0
        self._dy = 0
        self._voulu_milieu = False

    def close(self):
        """Appele a l'arret de main.py. Garantit que rien ne reste enfonce.

        UN BOUTON DU MILIEU RESTE ENFONCE EST PIRE QU'UN CTRL RESTE
        ENFONCE : la vue 3D tourne sans fin, et il faut aller cliquer dans
        le logiciel pour s'en sortir. On s'accorde donc 150 ms - le meme
        budget que le clavier - pour envoyer le relachement.
        """
        self._dx = 0
        self._dy = 0
        self._voulu_milieu = False
        if not self._etat_milieu:
            # Rien n'etait enfonce : il n'y a rien a reparer. On ne touche
            # pas a l'USB, et le REPL de Thonny reste disponible.
            return
        depart = ticks_ms()
        try:
            while ticks_diff(ticks_ms(), depart) < 150:
                if self.interface.is_open() and self.interface.rapport(False):
                    self._etat_milieu = False
                    return
                sleep_ms(1)
        except Exception as exc:
            print("Souris : liberation finale echouee", exc)
        print("Souris : bouton peut-etre encore enfonce cote PC.")
        print("Souris : un clic du milieu dans le logiciel 3D le liberera.")


def creer_interface():
    """Fabrique l'interface souris SANS la declarer a Windows.

    La declaration se fait ailleurs, en UN SEUL appel qui porte le clavier
    et la souris ensemble - c'est ce qu'on appelle un peripherique
    composite. Voir hid_keyboard.create_interface().
    """
    import usb.device                                    # noqa: F401
    from usb.device.hid import HIDInterface
    from usb.device.mouse import MouseInterface
    import struct

    class SourisNonBloquante(MouseInterface):
        """La souris officielle, mais qui rend toujours la main.

        On reecrit send_report() au lieu de l'appeler : voir l'explication
        complete en tete de fichier. L'ordre des bits est celui de la
        bibliotheque d'origine et du descripteur HID - bouton 1 (gauche) en
        bit 0, bouton 2 (droit) en bit 1, bouton 3 (milieu) en bit 2. Les
        intervertir donnerait une souris qui clique a cote.
        """

        def send_report(self, dx=0, dy=0, timeout_ms=0):
            if self.busy():
                # LA LIGNE QUI JUSTIFIE TOUT CE FICHIER. L'originale
                # attendait ici, sans limite. Nous, on renonce et on
                # reessaiera : l'appelant accumule le deplacement.
                return False
            octet = 0
            if self._l:
                octet |= 1 << 0
            if self._r:
                octet |= 1 << 1
            if self._m:
                octet |= 1 << 2
            struct.pack_into("Bbb", self._buf, 0, octet, dx, dy)
            return HIDInterface.send_report(self, self._buf, timeout_ms)

        def rapport(self, milieu, dx=0, dy=0):
            """Un seul rapport : l'etat du bouton du milieu et le mouvement."""
            self._m = bool(milieu)
            return self.send_report(dx, dy)

    return SourisNonBloquante(interface_str="Macropad 3D Mouse")
