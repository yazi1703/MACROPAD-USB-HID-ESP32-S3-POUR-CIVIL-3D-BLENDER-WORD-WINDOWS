# -*- coding: utf-8 -*-
"""
display.py - Interface utilisateur sur l'ecran OLED SH1106 128x64.

L'ecran est un CONFORT, jamais une dependance : si aucun OLED n'est detecte,
toutes les methodes deviennent des instructions vides et le macropad continue
de fonctionner normalement en clavier USB.

VUE NORMALE                        VUE CHANGEMENT DE PROFIL (~500 ms)
+----------------------+           +----------------------+
| CIVIL 3D        HID  |           |                      |
|----------------------|           |                      |
| B1      | B2         |           |   C I V I L  3 D     |   (police doublee)
| MATCH   | HATCH      |           |                      |
|---------|------------|           |                      |
| B3      | B4         |           +----------------------+
| UNDO    | ISOLE      |
+----------------------+

Le rafraichissement est etale sur plusieurs tours de boucle (voir sh1106.py),
donc l'affichage ne ralentit jamais la detection des touches.
"""

import time
import framebuf
from machine import Pin, I2C

import sh1106

# Geometrie de la vue normale
_TITLE_Y = 1
_SEP_Y = 12
_CELL_W = 64
_CELL_H = 26
_CELL_ORIGIN = ((0, 14), (64, 14), (0, 40), (64, 40))


def scan_i2c(i2c, candidates, verbose=True):
    """Scanne le bus et retourne l'adresse OLED trouvee, ou None."""
    try:
        found = i2c.scan()
    except Exception as exc:
        print("[OLED] bus I2C inutilisable :", exc)
        return None
    if verbose:
        print("[OLED] peripheriques I2C detectes :",
              ", ".join("0x%02X" % a for a in found) if found else "aucun")
    for address in candidates:
        if address in found:
            return address
    return None


class Display:
    """Vue OLED du macropad. Tolerante a l'absence d'ecran."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.ok = False
        self.oled = None
        self.address = None

        self._profile_title = ""
        self._labels = ("", "", "", "")
        self._status = ""
        self._splash_until = 0
        self._splash_active = False
        self._message_active = False
        self._highlight_index = -1
        self._highlight_until = 0

        try:
            i2c = I2C(cfg.I2C_BUS, scl=Pin(cfg.PIN_I2C_SCL),
                      sda=Pin(cfg.PIN_I2C_SDA), freq=cfg.I2C_FREQ)
        except Exception as exc:
            print("[OLED] initialisation I2C impossible :", exc)
            return

        self.address = scan_i2c(i2c, cfg.OLED_ADDRESSES, cfg.VERBOSE)
        if self.address is None:
            print("[OLED] ERREUR : aucun ecran a l'adresse 0x3C ou 0x3D.")
            print("[OLED] verifiez VCC/GND/SDA(GPIO%d)/SCL(GPIO%d)."
                  % (cfg.PIN_I2C_SDA, cfg.PIN_I2C_SCL))
            print("[OLED] le macropad continue sans affichage.")
            return

        try:
            self.oled = sh1106.SH1106_I2C(i2c, address=self.address,
                                          width=cfg.OLED_WIDTH,
                                          height=cfg.OLED_HEIGHT)
            self.ok = True
            print("[OLED] SH1106 initialise a l'adresse 0x%02X" % self.address)
        except Exception as exc:
            print("[OLED] driver SH1106 en echec :", exc)
            print("[OLED] le macropad continue sans affichage.")

    # ------------------------------------------------------------------
    # Rendu
    # ------------------------------------------------------------------
    def _draw_normal(self):
        oled = self.oled
        oled.fill(0)
        oled.text(self._profile_title[:14], 2, _TITLE_Y, 1)
        if self._status:
            x = self.cfg.OLED_WIDTH - 8 * len(self._status) - 1
            oled.text(self._status, x, _TITLE_Y, 1)
        oled.hline(0, _SEP_Y - 2, self.cfg.OLED_WIDTH, 1)
        oled.hline(0, 38, self.cfg.OLED_WIDTH, 1)
        oled.vline(_CELL_W - 1, _SEP_Y, self.cfg.OLED_HEIGHT - _SEP_Y, 1)
        for index in range(4):
            self._draw_cell(index, index == self._highlight_index)
        oled.mark_all()

    def _draw_cell(self, index, highlighted):
        oled = self.oled
        x, y = _CELL_ORIGIN[index]
        width = _CELL_W - 2
        background = 1 if highlighted else 0
        foreground = 0 if highlighted else 1
        oled.fill_rect(x, y, width, _CELL_H - 2, background)
        oled.text("B%d" % (index + 1), x + 2, y + 2, foreground)
        oled.text(self._labels[index][:7], x + 2, y + 13, foreground)
        oled.mark_rows(y, y + _CELL_H - 2)

    def _draw_big_text(self, text):
        """Ecrit un texte en police doublee, centre a l'ecran."""
        oled = self.oled
        oled.fill(0)
        if len(text) * 16 > self.cfg.OLED_WIDTH:
            # Trop long pour la police doublee : on reste en taille normale.
            x = max(0, (self.cfg.OLED_WIDTH - len(text) * 8) // 2)
            oled.text(text, x, (self.cfg.OLED_HEIGHT - 8) // 2, 1)
            oled.mark_all()
            return

        source_width = len(text) * 8
        buffer = bytearray(((source_width + 7) // 8) * 8)
        scratch = framebuf.FrameBuffer(buffer, source_width, 8,
                                       framebuf.MONO_HLSB)
        scratch.fill(0)
        scratch.text(text, 0, 0, 1)

        x0 = (self.cfg.OLED_WIDTH - source_width * 2) // 2
        y0 = (self.cfg.OLED_HEIGHT - 16) // 2
        for sy in range(8):
            for sx in range(source_width):
                if scratch.pixel(sx, sy):
                    oled.fill_rect(x0 + sx * 2, y0 + sy * 2, 2, 2, 1)
        oled.mark_all()

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def set_status(self, status):
        """Petit texte en haut a droite : HID, SAFE, ---"""
        self._status = status
        if self.ok and not self._splash_active and not self._message_active:
            self._draw_normal()

    def show_profile(self, title, labels, splash=True, now=None):
        """Affiche un profil. splash=True montre d'abord son nom en grand."""
        self._profile_title = title
        self._labels = tuple(labels)
        self._highlight_index = -1
        self._message_active = False
        if not self.ok:
            return
        now = time.ticks_ms() if now is None else now
        if splash:
            self._draw_big_text(title[:8])
            self._splash_active = True
            self._splash_until = time.ticks_add(now, self.cfg.SPLASH_MS)
        else:
            self._splash_active = False
            self._draw_normal()

    def highlight_macro(self, index, now=None):
        """Surligne brievement la case de la macro declenchee."""
        if not self.ok or self._splash_active or self._message_active:
            return
        now = time.ticks_ms() if now is None else now
        self._highlight_index = index
        self._highlight_until = time.ticks_add(now,
                                               self.cfg.MACRO_HIGHLIGHT_MS)
        self._draw_cell(index, True)

    def message(self, lines):
        """Affiche quelques lignes de texte brut (SAFE MODE, erreurs)."""
        if not self.ok:
            return
        self.oled.fill(0)
        y = 4
        for line in lines[:6]:
            self.oled.text(line[:16], 2, y, 1)
            y += 10
        self.oled.mark_all()
        self._splash_active = False
        self._message_active = True
        self._highlight_index = -1
        self.oled.show()

    def service(self, now):
        """A appeler a chaque tour de boucle : transitions + envoi I2C."""
        if not self.ok:
            return
        if self._splash_active and time.ticks_diff(now, self._splash_until) >= 0:
            self._splash_active = False
            self._draw_normal()
        if (self._highlight_index >= 0
                and time.ticks_diff(now, self._highlight_until) >= 0):
            index = self._highlight_index
            self._highlight_index = -1
            if not self._splash_active:
                self._draw_cell(index, False)
        try:
            self.oled.flush_step(self.cfg.OLED_PAGES_PER_SERVICE)
        except Exception as exc:
            # Un ecran debranche a chaud ne doit pas arreter le clavier.
            print("[OLED] communication perdue :", exc)
            self.ok = False
