# -*- coding: utf-8 -*-
"""
sh1106.py - Pilote minimal pour ecran OLED 1,3" SH1106 128x64 en I2C.

ORIGINE
-------
Adapte de deux sources sous licence MIT :
  - micropython/micropython-lib, driver ssd1306.py (structure FrameBuffer)
    Copyright (c) 2016 Radomir Dopieralski, Damien P. George
  - robert-hh/SH1106 (https://github.com/robert-hh/SH1106), sequence
    d'initialisation SH1106 et principe de mise a jour par pages
    Copyright (c) 2016-2021 Radomir Dopieralski, Robert Hammelrath, Tim Weber

PARTICULARITE DU SH1106
-----------------------
Contrairement au SSD1306, le SH1106 possede 132 colonnes de RAM pour une
dalle de 128 pixels : les colonnes 0 et 1 ne sont pas visibles. Il faut donc
decaler l'ecriture de 2 colonnes (COLUMN_OFFSET), sinon l'image est decalee.
Le SH1106 ne gere pas non plus l'adressage horizontal automatique : on ecrit
page par page (8 lignes de pixels a la fois).

RAFRAICHISSEMENT PARTIEL
------------------------
Envoyer les 8 pages d'un coup represente environ 1 ko sur l'I2C, soit ~23 ms
a 400 kHz. Ce serait un gel perceptible pour les touches. Le pilote memorise
donc quelles pages ont change (self._dirty) et flush_step() n'en envoie que
quelques-unes par appel : l'affichage se met a jour en plusieurs tours de
boucle sans jamais monopoliser le processeur.
"""

import framebuf

# Commandes SH1106
_SET_CONTRAST = 0x81
_SET_ENTIRE_ON = 0xA4
_SET_NORM_INV = 0xA6
_SET_DISP = 0xAE
_SET_DISP_START_LINE = 0x40
_SET_SEG_REMAP = 0xA0
_SET_MUX_RATIO = 0xA8
_SET_COM_OUT_DIR = 0xC0
_SET_DISP_OFFSET = 0xD3
_SET_COM_PIN_CFG = 0xDA
_SET_DISP_CLK_DIV = 0xD5
_SET_PRECHARGE = 0xD9
_SET_VCOM_DESEL = 0xDB
_SET_CHARGE_PUMP = 0xAD
_SET_PAGE_ADDRESS = 0xB0

COLUMN_OFFSET = 2


class SH1106_I2C(framebuf.FrameBuffer):
    """Ecran SH1106 128x64 sur bus I2C."""

    def __init__(self, i2c, address=0x3C, width=128, height=64,
                 rotate180=False):
        self.i2c = i2c
        self.address = address
        self.width = width
        self.height = height
        self.pages = height // 8
        self.rotate180 = rotate180

        self.buffer = bytearray(width * self.pages)
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)

        self._dirty = (1 << self.pages) - 1      # toutes les pages a envoyer
        self._next_page = 0
        self._cmd_buffer = bytearray(b"\x80\x00")   # reutilise, zero allocation
        self.init_display()

    # ------------------------------------------------------------------
    # Communication I2C
    # ------------------------------------------------------------------
    def write_cmd(self, *commands):
        """Envoie une ou plusieurs commandes de controle.

        Chaque commande part dans sa propre transaction, precedee de l'octet
        de controle 0x80 (Co=1, D/C=0). C'est exactement ce que font les
        pilotes officiels ssd1306.py et robert-hh/SH1106 : la forme la plus
        surement acceptee par les modules du commerce. Le surcout est
        negligeable (environ 70 us par commande a 400 kHz).
        """
        for command in commands:
            self._cmd_buffer[1] = command & 0xFF
            self.i2c.writeto(self.address, self._cmd_buffer)

    def write_data(self, view):
        """Envoie un bloc de donnees pixel (prefixe 0x40)."""
        try:
            self.i2c.writevto(self.address, (b"\x40", view))
        except AttributeError:
            # Repli si writevto n'existe pas sur ce portage.
            self.i2c.writeto(self.address, b"\x40" + bytes(view))

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def init_display(self):
        seg_remap = _SET_SEG_REMAP | (0x00 if self.rotate180 else 0x01)
        com_dir = _SET_COM_OUT_DIR | (0x00 if self.rotate180 else 0x08)
        self.write_cmd(
            _SET_DISP | 0x00,               # ecran eteint pendant la config
            _SET_DISP_CLK_DIV, 0x80,
            _SET_MUX_RATIO, self.height - 1,
            _SET_DISP_OFFSET, 0x00,
            _SET_DISP_START_LINE | 0x00,
            _SET_CHARGE_PUMP, 0x8B,         # convertisseur DC-DC interne actif
            0x32,                           # tension de pompe 8,0 V
            seg_remap,
            com_dir,
            _SET_COM_PIN_CFG, 0x12,
            _SET_CONTRAST, 0x80,
            _SET_PRECHARGE, 0x22,
            _SET_VCOM_DESEL, 0x35,
            _SET_ENTIRE_ON,                 # l'affichage suit la RAM
            _SET_NORM_INV,                  # video normale
        )
        self.fill(0)
        self.show()
        self.write_cmd(_SET_DISP | 0x01)    # ecran allume

    # ------------------------------------------------------------------
    # Rafraichissement
    # ------------------------------------------------------------------
    def mark_all(self):
        """Marque tout l'ecran comme a rafraichir."""
        self._dirty = (1 << self.pages) - 1

    def mark_rows(self, y_start, y_end):
        """Marque les pages couvrant la bande de pixels [y_start, y_end]."""
        if y_start < 0:
            y_start = 0
        if y_end > self.height - 1:
            y_end = self.height - 1
        for page in range(y_start // 8, y_end // 8 + 1):
            self._dirty |= 1 << page

    def is_dirty(self):
        return self._dirty != 0

    def _write_page(self, page):
        column = COLUMN_OFFSET
        self.write_cmd(
            _SET_PAGE_ADDRESS | page,
            0x00 | (column & 0x0F),         # colonne, poids faibles
            0x10 | (column >> 4),           # colonne, poids forts
        )
        start = page * self.width
        self.write_data(memoryview(self.buffer)[start:start + self.width])

    def flush_step(self, max_pages=2):
        """Envoie au plus max_pages pages modifiees. Retourne True s'il reste
        du travail pour le prochain appel."""
        sent = 0
        for _ in range(self.pages):
            if self._dirty == 0:
                return False
            page = self._next_page
            self._next_page = (page + 1) % self.pages
            if self._dirty & (1 << page):
                self._write_page(page)
                self._dirty &= ~(1 << page)
                sent += 1
                if sent >= max_pages:
                    return self._dirty != 0
        return self._dirty != 0

    def show(self):
        """Rafraichissement complet et bloquant (init, diagnostic)."""
        self.mark_all()
        while self.flush_step(self.pages):
            pass

    # ------------------------------------------------------------------
    # Confort
    # ------------------------------------------------------------------
    def contrast(self, value):
        self.write_cmd(_SET_CONTRAST, value & 0xFF)

    def invert(self, enable):
        self.write_cmd(_SET_NORM_INV | (1 if enable else 0))

    def poweroff(self):
        self.write_cmd(_SET_DISP | 0x00)

    def poweron(self):
        self.write_cmd(_SET_DISP | 0x01)
