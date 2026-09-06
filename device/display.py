# -*- coding: utf-8 -*-
"""
display.py - L'interface sur l'écran OLED SH1106 128x64.

=====================================================================
L'ÉCRAN N'EST JAMAIS INDISPENSABLE
=====================================================================
S'il est absent, débranché, ou s'il tombe en panne en cours de route, on
l'abandonne proprement (self.oled = None) et le macropad continue de
fonctionner comme clavier. Un écran ne doit jamais empêcher de taper.

=====================================================================
LA VUE PRINCIPALE, SIX TOUCHES
=====================================================================
    ┌────────────────────────┐
    │▓CIVIL 3D▓▓▓▓▓▓▓▓▓▓HID▓▓│   bandeau en vidéo inversée
    │ ▐1▌ MATCH   ▐2▌ HATCH  │
    │ ▐3▌ ANNUL   ▐4▌ ISOLE  │   trois lignes de deux touches
    │ ▐5▌ ZOOM    ▐6▌ ENREG  │
    │────────────────────────│
    │ ■ □ □ □                │   position dans la liste des profils
    └────────────────────────┘

Le numéro de chaque touche est dans une pastille en vidéo inversée : on
retrouve la bonne touche d'un coup d'œil, sans lire. Les libellés font
6 caractères au maximum, c'est ce que laisse la demi-largeur de l'écran.

Les petits carrés du bas indiquent où tu es dans la liste des profils,
comme les points d'un carrousel. Avec quatre profils tu vois quatre
carrés, dont un plein.

=====================================================================
POURQUOI UNE SEULE PAGE PAR TOUR DE BOUCLE
=====================================================================
L'écran fait 1024 octets. Les envoyer d'un coup prend environ 23 ms,
pendant lesquelles le processeur ne fait rien d'autre : on sentirait le
macropad accrocher à chaque changement d'affichage.

Le SH1106 range sa mémoire en 8 bandes horizontales de 8 pixels, appelées
pages. On en envoie UNE par tour de boucle, soit environ 3 ms. L'image
complète se met à jour en 8 tours, c'est-à-dire environ 16 ms : invisible
à l'œil, et les touches restent lues en permanence.

Particularité du SH1106 : il possède 132 colonnes de mémoire pour une
dalle de 128 pixels. Il faut décaler l'écriture de 2 colonnes, sinon toute
l'image est décalée. C'est le rôle de la commande 0x02 dans tick().
"""

from time import ticks_ms, ticks_diff, ticks_add
import config as C

# Géométrie de la vue principale
_TITRE_H = 11                       # hauteur du bandeau de titre
_LIGNES_Y = (14, 29, 44)            # ligne de base des trois rangées
_COLONNES_X = (0, 64)               # deux colonnes de 64 pixels
_SEPARATEUR_Y = 54
_PASTILLES_Y = 57


class Display:

    def __init__(self):
        self.oled = None
        self.titre = ""
        self.macros = []
        self.etat = ""
        self.document = ""          # nom du fichier ouvert, envoye par le PC
        self.pastilles = (0, 0)     # (index du profil courant, nombre total)
        self.splash_until = None
        self.pending_page = 8       # 8 = rien à envoyer ; 0 = tout à renvoyer
        if not C.OLED_ENABLED:
            return
        try:
            from machine import Pin, I2C
            from sh1106 import SH1106_I2C
            # timeout : si l'écran ne répond pas, l'échange est abandonné
            # au lieu de bloquer indéfiniment toute la boucle principale.
            bus = I2C(C.I2C_ID, sda=Pin(C.OLED_SDA), scl=Pin(C.OLED_SCL),
                      freq=C.I2C_FREQ, timeout=C.I2C_TIMEOUT_US)
            adresses = bus.scan()
            print("OLED I2C :", [hex(a) for a in adresses])
            adresse = next((a for a in (0x3c, 0x3d) if a in adresses), None)
            if adresse is None:
                raise OSError("SH1106 absent (0x3C/0x3D)")
            self.oled = SH1106_I2C(128, 64, bus, addr=adresse, rotate=0)
            self.oled.contrast(C.OLED_CONTRAST)
        except Exception as exc:
            self.disable(exc)

    def disable(self, erreur):
        """Abandonne l'écran sans arrêter le macropad."""
        print("OLED desactive :", erreur)
        self.oled = None

    # ------------------------------------------------------------------
    # Briques de dessin
    # ------------------------------------------------------------------
    def _bandeau(self, texte, droite=""):
        """Bandeau supérieur en vidéo inversée."""
        o = self.oled
        o.fill_rect(0, 0, 128, _TITRE_H, 1)      # rectangle plein
        o.text(texte[:13], 2, 2, 0)              # texte en noir sur blanc
        if droite:
            o.text(droite[:4], 128 - 8 * len(droite[:4]) - 2, 2, 0)

    def _pastille_touche(self, x, y, numero, label):
        """Une case : le numéro en vidéo inversée, puis le libellé."""
        o = self.oled
        o.fill_rect(x + 1, y - 1, 9, 10, 1)
        o.text(str(numero), x + 2, y, 0)
        o.text(label[:6], x + 12, y, 1)

    def _carrousel(self):
        """Petits carrés indiquant la position dans la liste des profils."""
        o = self.oled
        index, total = self.pastilles
        for i in range(min(total, 14)):
            x = 2 + i * 8
            if i == index:
                o.fill_rect(x, _PASTILLES_Y, 5, 5, 1)      # profil courant
            else:
                o.rect(x, _PASTILLES_Y, 5, 5, 1)

    def _vue_principale(self):
        o = self.oled
        o.fill(0)
        self._bandeau(self.titre, self.etat)
        for index in range(min(len(self.macros), 6)):
            x = _COLONNES_X[index % 2]
            y = _LIGNES_Y[index // 2]
            self._pastille_touche(x, y, index + 1, self.macros[index][0])
        o.hline(0, _SEPARATEUR_Y, 128, 1)
        # En bas : le nom du document si le PC nous l'envoie, sinon la
        # position dans la liste des profils. Le nom du fichier est plus
        # informatif, il a donc la priorite.
        if self.document:
            o.text(self.document[:16], 2, _PASTILLES_Y - 1, 1)
        else:
            self._carrousel()

    def _texte_double(self, texte):
        """Écrit un texte en police doublée, centré.

        MicroPython ne fournit qu'une police 8x8. Pour l'agrandir on dessine
        le texte dans une petite image en mémoire, puis on recopie chaque
        pixel sous forme d'un carré de 2x2 sur l'écran.
        """
        import framebuf
        o = self.oled
        o.fill(0)
        echelle = 2 if len(texte) <= 8 else 1
        largeur = len(texte) * 8
        tampon = framebuf.FrameBuffer(bytearray(128), 128, 8,
                                      framebuf.MONO_HLSB)
        tampon.text(texte, 0, 0, 1)
        x0 = max(0, (128 - largeur * echelle) // 2)
        y0 = (64 - 8 * echelle) // 2
        for x in range(min(128, largeur)):
            for y in range(8):
                if tampon.pixel(x, y):
                    o.fill_rect(x0 + x * echelle, y0 + y * echelle,
                                echelle, echelle, 1)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def message(self, *lignes):
        """Quelques lignes de texte brut : SAFE MODE, erreurs, diagnostic."""
        if not self.oled:
            return
        try:
            self.splash_until = None
            self.oled.fill(0)
            y = 4
            for ligne in lignes[:6]:
                self.oled.text(str(ligne)[:16], 2, y, 1)
                y += 10
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def config_screen(self, ssid, mot_de_passe, adresse):
        """Écran du mode configuration : tout ce qu'il faut pour se connecter."""
        if not self.oled:
            return
        try:
            o = self.oled
            o.fill(0)
            self._bandeau("MODE CONFIG", "WIFI")
            o.text("Reseau :", 2, 15, 1)
            o.text(str(ssid)[:16], 2, 25, 1)
            o.text("Cle :", 2, 36, 1)
            o.text(str(mot_de_passe)[:16], 2, 46, 1)
            o.hline(0, _SEPARATEUR_Y, 128, 1)
            o.text(str(adresse)[:16], 2, 56, 1)
            self.splash_until = None
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def set_document(self, texte):
        """Nom du document affiche en bas de l'ecran (envoye par le PC)."""
        texte = (texte or "")[:16]
        if texte == self.document:
            return
        self.document = texte
        if self.oled and self.splash_until is None:
            try:
                self._vue_principale()
                self.pending_page = 0
            except Exception as exc:
                self.disable(exc)

    def set_etat(self, etat):
        """Petit texte en haut à droite : HID, SAFE, ..."""
        self.etat = etat
        if self.oled and self.splash_until is None:
            try:
                self._vue_principale()
                self.pending_page = 0
            except Exception as exc:
                self.disable(exc)

    def profile(self, titre, macros, now, index=0, total=1, splash=False):
        """Affiche un profil.

        splash=True montre d'abord son nom en gros pendant une demi-seconde,
        puis on revient automatiquement à la vue à six touches.
        """
        self.titre = titre
        self.macros = list(macros)
        self.pastilles = (index, total)
        if not self.oled:
            return
        try:
            if splash:
                self._texte_double(titre[:8])
                self.splash_until = ticks_add(now, C.PROFILE_SPLASH_MS)
            else:
                self._vue_principale()
                self.splash_until = None
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def tick(self, now):
        """Envoie au plus UNE page. Appelé à chaque tour de boucle."""
        if not self.oled:
            return
        if self.splash_until is not None and ticks_diff(now, self.splash_until) >= 0:
            self.splash_until = None
            try:
                self._vue_principale()
                self.pending_page = 0
            except Exception as exc:
                self.disable(exc)
                return
        if not self.oled or self.pending_page >= 8:
            return
        try:
            page = self.pending_page
            self.oled.write_cmd(0xB0 | page)   # choisir la bande n° page
            self.oled.write_cmd(0x02)          # colonne de départ, poids faibles
            self.oled.write_cmd(0x10)          # colonne de départ, poids forts
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
        les touches ne deviennent actives, en SAFE MODE, en mode config.
        """
        for _ in range(8):
            self.tick(ticks_ms())
