# -*- coding: utf-8 -*-
"""
hid_keyboard.py - Couche clavier USB HID du macropad.

S'APPUIE SUR LA BIBLIOTHEQUE OFFICIELLE MICROPYTHON
---------------------------------------------------
    usb.device            (paquet micropython-lib "usb-device")
    usb.device.hid        (paquet "usb-device-hid")
    usb.device.keyboard   (paquet "usb-device-keyboard")
Ces paquets sont ecrits par Angus Gratton (licence MIT) et s'appuient sur la
classe bas niveau machine.USBDevice du firmware. Rien n'est reinvente ici.
Installation : voir README.md (mpremote mip install usb-device-keyboard).

CE QUE CE MODULE AJOUTE
-----------------------
1. La gestion de la disposition clavier Windows (AZERTY / QWERTY, cf keymaps.py).
2. Une FILE D'ATTENTE NON BLOQUANTE : ecrire "_ISOLATEOBJECTS" demande 30
   rapports USB espaces de 8 ms. Au lieu de bloquer 240 ms dans un sleep, les
   rapports sont empiles et envoyes un par un depuis la boucle principale.
   L'ecran, la LED, les TTP223 et surtout ESC restent donc reactifs.
3. La garantie de relachement : chaque appui est TOUJOURS suivi d'un rapport
   "toutes touches relachees". Aucun CTRL / WIN / SHIFT ne peut rester coince.
4. Un mode desactive (SAFE MODE) ou aucun rapport n'est jamais emis.
"""

import time
import keymaps

# --- Import de la pile USB HID -----------------------------------------
# Absente = le macropad demarre quand meme (diagnostic, ecran, boutons),
# mais sans clavier. L'erreur n'est jamais masquee silencieusement.
try:
    import usb.device
    from usb.device.keyboard import KeyboardInterface

    HID_LIB_AVAILABLE = True
    HID_LIB_ERROR = None
except ImportError as exc:  # pragma: no cover - depend du firmware
    HID_LIB_AVAILABLE = False
    HID_LIB_ERROR = str(exc)


class Keyboard:
    """Clavier USB HID avec file d'attente non bloquante."""

    def __init__(self, layout_name="FR_AZERTY", enabled=True,
                 report_interval_ms=8, queue_max=96, stall_timeout_ms=2000,
                 manufacturer="Yazid", product="Macropad CAO", verbose=True):
        self.layout_name = layout_name
        self.layout = keymaps.get_layout(layout_name)
        self.enabled = enabled              # False = SAFE MODE, aucun envoi
        self.available = False              # True quand l'interface USB est creee
        self.report_interval_ms = report_interval_ms
        self.queue_max = queue_max
        self.stall_timeout_ms = stall_timeout_ms
        self.manufacturer = manufacturer
        self.product = product
        self.verbose = verbose

        self._itf = None
        self._queue = []        # liste de (masque_modificateurs, tuple_de_codes)
        self._head = 0          # index du prochain rapport a envoyer
        self._last_send_ms = 0
        self._queued_since_ms = 0
        self._unknown_chars = []

    # ------------------------------------------------------------------
    # Demarrage
    # ------------------------------------------------------------------
    def start(self):
        """Cree l'interface HID et (re)configure le peripherique USB.

        Retourne True si le clavier HID est operationnel.

        ATTENTION : cet appel reconfigure le peripherique USB, donc le port
        USB natif se re-enumere. Sous Windows le port COM du REPL disparait
        puis revient. C'est normal. Pour travailler confortablement dans
        Thonny, utilisez le second port USB-C (USB-UART) de la carte.
        """
        if not self.enabled:
            self._log("HID desactive (SAFE MODE) : aucune touche ne sera envoyee")
            return False

        if not HID_LIB_AVAILABLE:
            print("[HID] ERREUR : bibliotheque usb.device.keyboard absente.")
            print("[HID] detail :", HID_LIB_ERROR)
            print("[HID] installez-la depuis le PC :")
            print("[HID]    mpremote connect COMx mip install usb-device-keyboard")
            return False

        try:
            self._itf = KeyboardInterface()
            usb.device.get().init(
                self._itf,
                builtin_driver=True,          # conserve le REPL USB CDC
                manufacturer_str=self.manufacturer,
                product_str=self.product,
            )
        except Exception as exc:
            # Erreur critique : on la montre, on ne la cache pas.
            print("[HID] ERREUR d'initialisation USB :", exc)
            self._itf = None
            self.available = False
            return False

        self.available = True
        self._last_send_ms = time.ticks_ms()
        self._log("clavier HID initialise (disposition %s)" % self.layout_name)
        return True

    def is_ready(self):
        """True si l'hote USB a bien configure l'interface clavier."""
        if not (self.enabled and self.available and self._itf is not None):
            return False
        try:
            return self._itf.is_open()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Traduction nom de touche -> (codes, modificateurs)
    # ------------------------------------------------------------------
    def _resolve(self, name):
        """Traduit un element de macro en (code HID ou None, masque modif).

        - "CTRL", "SHIFT", "ALT", "WIN"  -> (None, masque)
        - "TAB", "ESC", "F5", ...        -> (code, 0)
        - "G", "z", "1"                  -> touche PHYSIQUE qui produit ce
          caractere avec la disposition Windows choisie. Les modificateurs de
          la table sont ignores : un raccourci vise une touche, pas un signe.
        """
        if not isinstance(name, str):
            raise ValueError("nom de touche invalide : %r" % (name,))

        upper = name.upper()
        if upper in keymaps.MODIFIERS:
            return None, keymaps.MODIFIERS[upper]
        if upper in keymaps.NAMED_KEYS:
            return keymaps.NAMED_KEYS[upper], 0

        if len(name) == 1:
            entry = self.layout.get(name)
            if entry is None:
                entry = self.layout.get(name.lower())
            if entry is not None:
                return entry[0], 0      # raccourci : on ignore SHIFT/ALTGR
        raise ValueError("touche inconnue dans la macro : %r" % (name,))

    # ------------------------------------------------------------------
    # File d'attente
    # ------------------------------------------------------------------
    def _push_stroke(self, mod_mask, codes):
        """Un appui complet : touches enfoncees puis TOUT relache.

        Les deux rapports sont empiles ensemble ou pas du tout : il est
        impossible d'empiler un appui sans son relachement.
        """
        if not (self.enabled and self.available):
            return False
        if self.pending() + 2 > self.queue_max:
            print("[HID] file saturee, macro ignoree")
            return False
        if not self._queue:
            self._queued_since_ms = time.ticks_ms()
        self._queue.append((mod_mask, codes))
        self._queue.append((0, ()))     # relachement garanti
        return True

    def pending(self):
        return len(self._queue) - self._head

    def clear(self):
        """Vide la file et programme un relachement general."""
        self._queue = []
        self._head = 0
        self._queue.append((0, ()))
        self._queued_since_ms = time.ticks_ms()

    # ------------------------------------------------------------------
    # API publique des macros
    # ------------------------------------------------------------------
    def tap(self, key):
        """Une touche seule : tap("TAB"), tap("G"), tap("F5")."""
        code, mod = self._resolve(key)
        codes = () if code is None else (code,)
        return self._push_stroke(mod, codes)

    def combo(self, *keys):
        """Une combinaison : combo("CTRL", "Z"), combo("CTRL", "SHIFT", "ESC")."""
        mod_mask = 0
        codes = []
        for key in keys:
            code, mod = self._resolve(key)
            mod_mask |= mod
            if code is not None and len(codes) < 6:
                codes.append(code)
        return self._push_stroke(mod_mask, tuple(codes))

    def type_text(self, text, enter=False):
        """Ecrit une chaine caractere par caractere selon la disposition."""
        ok = True
        for char in text:
            entry = self.layout.get(char)
            if entry is None:
                if char not in self._unknown_chars:
                    self._unknown_chars.append(char)
                    print("[HID] caractere absent de la table %s : %r"
                          % (self.layout_name, char))
                ok = False
                continue
            code, mod = entry
            if not self._push_stroke(mod, (code,)):
                return False
        if enter:
            self._push_stroke(0, (keymaps.K_ENTER,))
        return ok

    def press_escape(self):
        """ESC prioritaire : annule tout ce qui etait en cours puis envoie ESC.

        C'est le comportement attendu d'une touche d'annulation : si une
        commande Civil 3D etait en train d'etre tapee, on ne veut pas que la
        fin de la chaine parte apres l'ESC.
        """
        if not (self.enabled and self.available):
            return False
        self._queue = []
        self._head = 0
        self._queue.append((0, (keymaps.K_ESC,)))
        self._queue.append((0, ()))
        self._queued_since_ms = time.ticks_ms()
        # Autorise un envoi des le prochain tour de boucle.
        self._last_send_ms = time.ticks_add(time.ticks_ms(),
                                            -self.report_interval_ms)
        return True

    # ------------------------------------------------------------------
    # A appeler a chaque tour de la boucle principale
    # ------------------------------------------------------------------
    def service(self, now):
        """Envoie au plus un rapport HID. Ne bloque jamais."""
        if self._head >= len(self._queue):
            if self._queue:
                self._queue = []
                self._head = 0
            return

        if not self.is_ready():
            # Hote absent ou pas encore pret : on patiente, puis on abandonne.
            if time.ticks_diff(now, self._queued_since_ms) > self.stall_timeout_ms:
                print("[HID] hote USB indisponible, file abandonnee")
                self._queue = []
                self._head = 0
            return

        if time.ticks_diff(now, self._last_send_ms) < self.report_interval_ms:
            return

        mod_mask, codes = self._queue[self._head]
        keys = []
        if mod_mask:
            keys.append(-mod_mask)      # la bibliotheque code les modificateurs
            # en valeurs negatives (voir usb/device/keyboard.py)
        keys.extend(codes)

        try:
            sent = self._itf.send_keys(keys, timeout_ms=0)
        except Exception as exc:
            print("[HID] erreur d'envoi :", exc)
            self._queue = []
            self._head = 0
            self.release_all_now()
            return

        if sent:
            self._head += 1
            self._last_send_ms = now
            self._queued_since_ms = now
            if self._head >= len(self._queue):
                self._queue = []
                self._head = 0
        elif time.ticks_diff(now, self._queued_since_ms) > self.stall_timeout_ms:
            print("[HID] envoi bloque, file videe et touches relachees")
            self._queue = []
            self._head = 0
            self.release_all_now()

    def release_all_now(self):
        """Relachement immediat de toutes les touches (filet de securite)."""
        if not (self.available and self._itf is not None):
            return
        try:
            self._itf.send_keys((), timeout_ms=50)
        except Exception as exc:
            print("[HID] relachement impossible :", exc)

    # ------------------------------------------------------------------
    def _log(self, message):
        if self.verbose:
            print("[HID]", message)
