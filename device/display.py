# -*- coding: utf-8 -*-
"""
display.py - L'écran OLED. Totalement facultatif.

=====================================================================
L'ECRAN N'EST JAMAIS INDISPENSABLE
=====================================================================
S'il est absent, débranché, ou s'il tombe en panne en cours de route, on
l'abandonne proprement (self.oled = None) et le macropad continue de
fonctionner comme clavier. Un écran ne doit jamais empêcher de taper.

=====================================================================
POURQUOI UNE SEULE PAGE PAR TOUR DE BOUCLE
=====================================================================
L'écran fait 128 x 64 pixels, soit 1024 octets. Les envoyer d'un coup sur
le bus I2C prend environ 23 millisecondes, pendant lesquelles le
processeur ne fait rien d'autre : on sentirait le macropad "accrocher" à
chaque changement d'affichage.

Le SH1106 organise sa mémoire en 8 bandes horizontales de 8 pixels de
haut, appelées "pages". On en envoie UNE par tour de boucle, soit environ
3 ms. L'image complète est donc mise à jour en 8 tours de boucle, c'est-
à-dire environ 16 ms : invisible pour l'oeil, et les touches restent
lues en permanence.

=====================================================================
PARTICULARITE DU SH1106
=====================================================================
Ce contrôleur possède 132 colonnes de mémoire pour une dalle de 128
pixels : les deux premières colonnes ne sont pas visibles. Il faut donc
décaler l'écriture de 2 colonnes, sinon toute l'image est décalée.
C'est le rôle de la commande 0x02 dans tick().
"""

from time import ticks_ms, ticks_diff, ticks_add
import config as C
from profiles import PROFILES, TITLES


class Display:

    def __init__(self):
        self.oled = None
        self.profile_name = C.DEFAULT_PROFILE
        self.splash_until = None
        self.pending_page = 8      # 8 = rien à envoyer ; 0 = tout à renvoyer
        if not C.OLED_ENABLED:
            return
        try:
            from machine import Pin, I2C
            from sh1106 import SH1106_I2C
            # timeout : si l'écran ne répond pas, l'échange est abandonné
            # au lieu de bloquer indéfiniment toute la boucle principale.
            bus = I2C(C.I2C_ID, sda=Pin(C.OLED_SDA), scl=Pin(C.OLED_SCL),
                      freq=C.I2C_FREQ, timeout=C.I2C_TIMEOUT_US)
            addresses = bus.scan()
            print("OLED I2C :", [hex(a) for a in addresses])
            address = next((a for a in (0x3c, 0x3d) if a in addresses), None)
            if address is None:
                raise OSError("SH1106 absent (0x3C/0x3D)")
            self.oled = SH1106_I2C(128, 64, bus, addr=address, rotate=0)
            self.oled.contrast(C.OLED_CONTRAST)
        except Exception as exc:
            self.disable(exc)

    def disable(self, error):
        """Abandonne l'écran sans arrêter le macropad."""
        print("OLED desactive :", error)
        self.oled = None

    def message(self, line1, line2=""):
        """Deux lignes de texte brut : SAFE MODE, erreurs, diagnostic."""
        if not self.oled:
            return
        try:
            self.splash_until = None
            self.oled.fill(0)                    # efface l'image en mémoire
            self.oled.text(line1[:16], 0, 20)    # 16 caractères par ligne max
            self.oled.text(line2[:16], 0, 36)
            self.pending_page = 0                # demande le réaffichage
        except Exception as exc:
            self.disable(exc)

    def profile(self, name, now, splash=False):
        """Affiche un profil.

        splash=True affiche d'abord son nom en gros pendant une demi-seconde,
        puis on revient automatiquement à la liste des quatre touches.
        """
        self.profile_name = name
        if not self.oled:
            return
        try:
            o = self.oled
            o.fill(0)
            title = TITLES.get(name, name)

            if splash:
                # MicroPython ne fournit qu'une seule police, en 8x8 pixels.
                # Pour l'agrandir, on dessine le texte dans une petite image
                # en mémoire, puis on recopie chaque pixel sous forme d'un
                # carré de 2x2 pixels sur l'écran.
                import framebuf
                scale = 2 if len(title) <= 8 else 1
                buf = framebuf.FrameBuffer(bytearray(128), 128, 8,
                                           framebuf.MONO_HLSB)
                buf.text(title, 0, 0, 1)
                x0 = max(0, (128 - len(title) * 8 * scale) // 2)   # centrage
                for x in range(min(128, len(title) * 8)):
                    for y in range(8):
                        if buf.pixel(x, y):
                            o.fill_rect(x0 + x * scale, 24 + y * scale,
                                        scale, scale, 1)
                self.splash_until = ticks_add(now, C.PROFILE_SPLASH_MS)
            else:
                o.text(title[:16], 0, 0)
                o.hline(0, 11, 128, 1)
                # Une ligne par touche : "B1 EXPLORER" tient entièrement,
                # pas besoin d'abréviations difficiles à relire.
                for i, macro in enumerate(PROFILES[name]):
                    o.text("B%d %s" % (i + 1, macro[0]), 0, 16 + i * 12)
                self.splash_until = None

            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def tick(self, now):
        """Envoie au plus UNE page à l'écran. Appelé à chaque tour de boucle."""
        if not self.oled:
            return
        if self.splash_until is not None and ticks_diff(now, self.splash_until) >= 0:
            self.profile(self.profile_name, now)     # fin du nom en gros
        if not self.oled or self.pending_page >= 8:
            return
        try:
            page = self.pending_page
            self.oled.write_cmd(0xB0 | page)   # choisir la bande n° page
            self.oled.write_cmd(0x02)          # colonne de départ, 4 bits bas
            self.oled.write_cmd(0x10)          # colonne de départ, 4 bits hauts
            #        ^ 0x02 = le décalage de 2 colonnes propre au SH1106
            self.oled.write_data(
                self.oled.displaybuf[page * 128:(page + 1) * 128])
            self.pending_page += 1
        except Exception as exc:
            # Un écran arraché en cours de route ne doit pas arrêter le clavier.
            self.disable(exc)

    def flush_startup(self):
        """Envoie l'image entière d'un coup.

        Réservé aux moments où l'on peut se permettre d'attendre : avant que
        les touches ne deviennent actives, et au retour au REPL en SAFE MODE.
        """
        for _ in range(8):
            self.tick(ticks_ms())
