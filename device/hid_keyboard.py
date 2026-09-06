# -*- coding: utf-8 -*-
"""
hid_keyboard.py - Le clavier USB proprement dit.

=====================================================================
CE QUE FAIT CE FICHIER, EN LANGAGE SIMPLE
=====================================================================

Il s'appuie sur la bibliothèque OFFICIELLE de MicroPython, recopiée telle
quelle dans device/lib/usb/device/ (licence MIT, auteur Angus Gratton).
Nous ne réécrivons pas l'USB : nous l'utilisons.

Son travail à lui, c'est de transformer

    "appuie sur Ctrl+Z"        (ce que dit profiles.py)

en une suite de RAPPORTS USB, c'est-à-dire des petits paquets de 8 octets
envoyés à Windows :

    paquet 1 : Ctrl enfoncé + touche Z enfoncée
    paquet 2 : plus rien d'enfoncé          <-- INDISPENSABLE

Le paquet 2 s'appelle le "relâchement". S'il n'est pas envoyé, Windows croit
que tu tiens Ctrl appuyé pour toujours : tes clics deviennent des sélections
multiples, ta souris zoome au lieu de défiler... C'est LA panne classique
d'un clavier programmable. Ce fichier garantit qu'un relâchement suit
toujours un appui, y compris quand une erreur se produit.

=====================================================================
POURQUOI CE CODE N'ATTEND JAMAIS
=====================================================================

Écrire "_ISOLATEOBJECTS" demande 32 paquets USB espacés d'environ 24 ms,
soit près de 400 ms au total. Si on faisait cela avec des sleep(), pendant
400 ms le macropad serait sourd : l'écran figé, le bouton ESC inopérant.

Alors on découpe. La méthode tick() est appelée en boucle par main.py et
n'envoie qu'UN paquet, celui qui est dû à cet instant, puis rend la main.
C'est ce qu'on appelle une machine à états : la variable self.phase se
souvient où on en est ("press" = il faut appuyer, "release" = il faut
relâcher).

=====================================================================
VOCABULAIRE DES VARIABLES
=====================================================================
  queue           : les macros en attente
  current         : la macro en cours, déjà traduite en frappes
  position        : où on en est dans current
  phase           : "idle" (rien à faire), "press" ou "release"
  due             : l'instant avant lequel il ne faut rien envoyer
  progress        : dernier instant où quelque chose a réellement avancé
                    (sert à détecter un blocage)
  release_needed  : il faut envoyer un paquet "plus rien d'enfoncé"
  keys_down       : vrai si le dernier paquet envoyé tenait des touches
  fault           : une panne grave est survenue, on n'envoie plus rien
"""

from time import ticks_ms, ticks_diff, ticks_add, sleep_ms
import config as C
from layouts import compile_actions


class HIDKeyboard:

    def __init__(self, interface):
        self.interface = interface     # l'objet clavier de la bibliothèque officielle
        self.queue = []
        self.current = []
        self.position = 0
        self.phase = "idle"
        self.due = ticks_ms()
        self.progress = self.due
        self.opened = False            # Windows a-t-il configuré le clavier ?
        self.release_needed = True     # par sécurité on commence par tout relâcher
        self.keys_down = False         # des touches sont-elles enfoncées côté PC ?
        self.fault = False

    # ------------------------------------------------------------------
    # Etats
    # ------------------------------------------------------------------
    def accepting(self):
        """Peut-on accepter une nouvelle macro ?

        Il suffit que Windows ait ouvert l'interface et qu'aucune panne ne
        soit déclarée. On n'exige PAS que le relâchement en attente soit
        déjà parti : sinon une touche pressée juste après un changement de
        profil ou après ESC serait perdue (c'était un défaut de la version
        précédente, la macro disparaissait sans explication).
        """
        return self.opened and not self.fault

    def ready(self):
        """Vrai quand le clavier est ouvert ET au repos complet."""
        return self.opened and not self.release_needed and not self.fault

    def idle(self):
        return self.phase == "idle" and not self.queue and not self.release_needed

    # ------------------------------------------------------------------
    # Entrée des macros
    # ------------------------------------------------------------------
    def submit(self, actions):
        """Met une macro en file d'attente. Ne tape rien tout de suite."""
        if not self.accepting():
            print("HID : action ignoree, interface non prete")
            return False
        # On traduit la macro TOUT DE SUITE, uniquement pour la vérifier.
        # Si un caractère est impossible, l'erreur remonte ici et rien n'a
        # encore été tapé. Mieux vaut ne rien écrire qu'écrire à moitié.
        compile_actions(actions, C.KEYBOARD_LAYOUT)
        if len(self.queue) >= C.MACRO_QUEUE_LIMIT:
            # On refuse plutôt que d'empiler : sinon un appui nerveux sur
            # une touche déclencherait dix commandes une minute plus tard.
            print("HID : file pleine, action ignoree")
            return False
        self.queue.append(actions)
        return True

    def cancel(self):
        """Oublie tout ce qui était prévu et programme un relâchement."""
        self.queue = []
        self.current = []
        self.phase = "idle"
        self.release_needed = True

    def escape(self, now):
        """Bouton ESC : priorité absolue.

        On jette ce qui était en cours (une commande Civil 3D à moitié
        tapée, par exemple), on relâche tout, puis on envoie Échap.
        C'est le comportement attendu d'une touche d'annulation.
        """
        self.cancel()
        self.due = now              # autorise un envoi dès le prochain tick
        self.progress = now
        if self.opened and not self.fault:
            self.queue.append([("key", "ESC")])

    # ------------------------------------------------------------------
    # Envoi bas niveau
    # ------------------------------------------------------------------
    def _send(self, keys):
        """Envoie un paquet, ou renonce immédiatement si l'USB est occupé.

        timeout_ms=0 veut dire « n'attends pas ». La bibliothèque rend la
        main tout de suite si le précédent paquet n'est pas encore parti ;
        on réessaiera au tour de boucle suivant. C'est ce qui garantit que
        le macropad ne se fige jamais.
        """
        if self.interface.busy():
            return False
        if not self.interface.send_keys(keys, timeout_ms=0):
            return False
        # On mémorise si ce paquet laissait des touches enfoncées.
        self.keys_down = bool(keys)
        return True

    def _fail(self, error):
        if not self.fault:
            print("ERREUR CRITIQUE HID :", error, "- macros arretees, RESET requis")
        self.fault = True
        self.cancel()

    # ------------------------------------------------------------------
    # Le coeur : appelé à chaque tour de la boucle principale
    # ------------------------------------------------------------------
    def tick(self, now):
        try:
            opened = self.interface.is_open()

            if not opened:
                # Câble débranché, PC en veille, ou Windows a réinitialisé
                # le port. On jette la file : hors de question qu'une macro
                # reparte toute seule au rebranchement.
                if self.opened:
                    print("HID : deconnexion/reset USB, file annulee")
                self.opened = False
                self.keys_down = False   # le PC a de toute façon tout oublié
                self.cancel()
                self.progress = now
                return

            if not self.opened:
                print("HID : interface ouverte par Windows")
                self.opened = True
                self.progress = now

            # Garde-fou : si plus rien n'avance alors qu'on a du travail,
            # c'est que l'USB est bloqué. On arrête tout plutôt que de
            # laisser une touche enfoncée indéfiniment.
            if (ticks_diff(now, self.progress) > C.HID_TIMEOUT_MS
                    and (self.release_needed or self.phase != "idle")):
                self._fail("transfert sans progression")

            # Priorité n° 1 : relâcher.
            if self.release_needed:
                if self._send(()):
                    self.release_needed = False
                    self.progress = now
                return

            if self.fault or ticks_diff(now, self.due) < 0:
                return

            # Priorité n° 2 : démarrer la macro suivante.
            if self.phase == "idle":
                if not self.queue:
                    return
                actions = self.queue.pop(0)
                # Windows nous dit si Verr. Maj est allumé (voyant du clavier).
                # On en tient compte au moment de traduire (voir layouts.py).
                caps = bool(getattr(self.interface, "led_mask", 0) & 2)
                self.current = compile_actions(actions, C.KEYBOARD_LAYOUT, caps)
                self.position = 0
                self.progress = now
                self.phase = "press"

            # Priorité n° 3 : dérouler la macro, une frappe par tick.
            if self.phase == "press":
                if self.position >= len(self.current):
                    self.phase = "idle"      # macro terminée
                    return
                if self._send(self.current[self.position]):
                    self.phase = "release"
                    self.due = ticks_add(now, C.KEY_HOLD_MS)
                    self.progress = now
            elif self.phase == "release":
                if self._send(()):
                    self.position += 1
                    self.phase = "press"
                    self.due = ticks_add(now, C.KEY_GAP_MS)
                    self.progress = now

        except Exception as exc:
            # Aucune exception ne doit remonter jusqu'à la boucle principale.
            self._fail(exc)

    # ------------------------------------------------------------------
    # Arrêt
    # ------------------------------------------------------------------
    def close(self):
        """Appelé quand main.py s'arrête (Ctrl-C dans Thonny, ou erreur).

        Objectif : ne JAMAIS laisser Ctrl, Alt, Maj ou Windows enfoncés
        côté PC. On dispose de 150 ms pour envoyer le paquet de relâchement.
        """
        self.cancel()

        if not self.keys_down:
            # Rien n'était enfoncé : il n'y a rien à réparer, on s'arrête
            # proprement sans toucher à l'USB. Le REPL de Thonny reste
            # disponible. (La version précédente coupait l'USB dans tous les
            # cas, ce qui faisait disparaître le port COM sans raison.)
            return

        start = ticks_ms()
        try:
            while ticks_diff(ticks_ms(), start) < 150:
                if self.interface.is_open() and self._send(()):
                    while (self.interface.busy()
                           and ticks_diff(ticks_ms(), start) < 150):
                        sleep_ms(1)
                    if not self.interface.busy():
                        return       # relâchement confirmé, tout va bien
                sleep_ms(1)
        except Exception as exc:
            print("HID : liberation finale echouee", exc)

        # Dernier recours : impossible de relâcher, et des touches restent
        # enfoncées côté PC. On débranche logiquement le clavier : pour
        # Windows le périphérique disparaît, donc les touches aussi.
        # Effet de bord assumé : le port COM du REPL natif disparaît aussi,
        # un RESET matériel le fait revenir.
        print("HID : touches encore enfoncees, deconnexion USB de securite")
        print("HID : appuyer sur RESET pour recuperer le port")
        import usb.device
        usb.device.get().active(False)


def create_interface():
    """Crée le clavier USB et le déclare à Windows.

    Appelé UNE SEULE FOIS depuis boot.py. À cet instant Windows découvre un
    nouveau périphérique : le port COM du REPL natif se ferme et se rouvre.
    C'est normal, ce n'est pas une panne.

    builtin_driver=True demande à MicroPython de GARDER le port série CDC
    en plus du clavier. Sans lui, on perdrait le REPL sur le port natif.
    """
    import machine
    if not hasattr(machine, "USBDevice"):
        raise RuntimeError(
            "machine.USBDevice absent : utiliser MicroPython >= 1.27 "
            "ESP32_GENERIC_S3 SPIRAM octale")
    import usb.device
    from usb.device.keyboard import KeyboardInterface

    class KeyboardWithLEDs(KeyboardInterface):
        """Même clavier, mais qui retient l'état des voyants du PC.

        Windows envoie au clavier l'état de Verr. Maj / Verr. Num. On s'en
        sert dans layouts.py pour taper le bon caractère (voir l'explication
        du piège Verr. Maj sur les claviers français).
        """

        def __init__(self):
            self.led_mask = 0
            super().__init__()

        def on_led_update(self, mask):
            self.led_mask = mask

    interface = KeyboardWithLEDs()
    usb.device.get().init(interface, builtin_driver=True)
    return interface
