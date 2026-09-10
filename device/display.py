# -*- coding: utf-8 -*-
"""
display.py - L'interface sur l'ecran OLED SH1106 128x64.

=====================================================================
L'ECRAN N'EST JAMAIS INDISPENSABLE
=====================================================================
S'il est absent, debranche, ou s'il tombe en panne en cours de route, on
l'abandonne proprement (self.oled = None) et le macropad continue de
fonctionner comme clavier. Un ecran ne doit jamais empecher de taper.

=====================================================================
LA VUE PRINCIPALE : UN TABLEAU DES GESTES
=====================================================================
    +------------------------+
    |#CIVIL 3D#########AUTO##|  bandeau inverse : profil + etat
    |   CRT   LNG   DBL      |  en-tete des trois colonnes
    |#1#MATC  ---   ---      |  ligne surlignee = touche qui vient de servir
    | 2 HATC  ---   ---      |
    | 3 ANNU  REFA  ---      |
    | 4 ISOL  UNIS  ---      |
    |------------------------|
    |C3D Projet_A12_Phas...  |  logiciel fixe + nom de fichier qui defile
    +------------------------+

Chaque ligne montre les trois macros d'une touche :
  CRT = appui court, LNG = appui long, DBL = double appui.
Un tiret signale un geste sans macro.

Quatre lignes tiennent a l'ecran. Avec six touches, le tableau **defile
tout seul** d'un cran toutes les TABLE_SCROLL_MS.

Et surtout : **des que tu appuies sur une touche, le tableau saute
instantanement dessus et la surligne**. Tu vois donc ce que tu viens de
declencher, et les deux autres gestes disponibles sur cette meme touche.

=====================================================================
POURQUOI UNE SEULE PAGE PAR TOUR DE BOUCLE
=====================================================================
L'ecran fait 1024 octets. Les envoyer d'un coup prend environ 23 ms,
pendant lesquelles le processeur ne fait rien d'autre : on sentirait le
macropad accrocher a chaque changement d'affichage.

Le SH1106 range sa memoire en 8 bandes horizontales de 8 pixels, les
"pages". On en envoie UNE par tour de boucle, soit environ 3 ms. L'image
complete se met a jour en 8 tours, environ 16 ms : invisible a l'oeil.

Le defilement du nom de fichier, lui, ne touche que la derniere ligne :
on ne reenvoie donc que la page 7, huit fois moins de trafic.

Particularite du SH1106 : 132 colonnes de memoire pour une dalle de 128
pixels. Il faut decaler l'ecriture de 2 colonnes, sinon toute l'image est
decalee. C'est le role de la commande 0x02 dans tick().

=====================================================================
ANTI-MARQUAGE
=====================================================================
Un OLED qui affiche la meme image pendant des heures MARQUE : les pixels
allumes en permanence vieillissent plus vite et laissent un fantome
definitif. Le bandeau inverse du haut est exactement le pire cas.

Apres SCREEN_DIM_MS sans appui on baisse le contraste, apres
SCREEN_OFF_MS on eteint la dalle. N'importe quelle touche reveille tout
instantanement.
"""

from time import ticks_ms, ticks_diff, ticks_add
import config as C

# Geometrie
_ENTETE_Y = 12                      # ligne des titres de colonnes
_LIGNE_Y = (21, 29, 37, 45)         # les quatre lignes visibles du tableau
_LIGNES_VISIBLES = len(_LIGNE_Y)
_SEPARATEUR_Y = 53
_BAS_Y = 55                         # ligne du document
# Les trois colonnes du tableau : abscisse en pixels, largeur en
# caracteres. La police fait 8 pixels de large, donc :
#   1 chiffre (8) + 6 caracteres (48) + 4 (32) + 4 (32) = 120 sur 128.
# La premiere colonne est la plus large parce qu'elle porte le libelle,
# que tu as le droit d'ecrire sur 6 caracteres (LABEL_MAX).
_COL_X = (8, 58, 92)                # colonnes court / long / double
_COL_LARGEUR = (6, 4, 4)            # caracteres par colonne

# Etats de l'economiseur d'ecran
_VEILLE_NORMALE = 0
_VEILLE_ATTENUEE = 1
_VEILLE_ETEINTE = 2


class Display:

    def __init__(self):
        self.oled = None
        self.titre = ""
        self.macros = []
        self.etat = ""
        self.doc_abrege = ""
        self.doc_nom = ""

        self._defil_x = 0           # decalage du nom de fichier, en pixels
        self._defil_sens = 1
        self._defil_max = 0
        self._defil_t = 0

        self.fenetre = 0            # index de la premiere touche affichee
        self._fenetre_t = 0         # prochain defilement automatique
        self.surbrillance = -1      # touche surlignee, -1 = aucune
        self._surbrillance_t = 0

        self.splash_until = None
        self.pending_page = 8       # 8 = rien a envoyer ; 0 = tout a renvoyer

        self._veille = _VEILLE_NORMALE
        self._activite = 0

        if not C.OLED_ENABLED:
            return
        try:
            from machine import Pin, I2C
            from sh1106 import SH1106_I2C
            # timeout : si l'ecran ne repond pas, l'echange est abandonne
            # au lieu de bloquer indefiniment toute la boucle principale.
            bus = I2C(C.I2C_ID, sda=Pin(C.OLED_SDA), scl=Pin(C.OLED_SCL),
                      freq=C.I2C_FREQ, timeout=C.I2C_TIMEOUT_US)
            adresses = bus.scan()
            print("OLED I2C :", [hex(a) for a in adresses])
            adresse = next((a for a in (0x3c, 0x3d) if a in adresses), None)
            if adresse is None:
                raise OSError("SH1106 absent (0x3C/0x3D)")
            self.oled = SH1106_I2C(128, 64, bus, addr=adresse, rotate=0)
            self.oled.contrast(C.OLED_CONTRAST)
            self._activite = ticks_ms()
        except Exception as exc:
            self.disable(exc)

    def disable(self, erreur):
        """Abandonne l'ecran sans arreter le macropad."""
        print("OLED desactive :", erreur)
        self.oled = None

    # ==================================================================
    # Briques de dessin
    # ==================================================================
    def _bandeau(self):
        o = self.oled
        o.fill_rect(0, 0, 128, 11, 1)
        o.text(self.titre[:13], 2, 2, 0)
        if self.etat:
            o.text(self.etat[:4], 128 - 8 * len(self.etat[:4]) - 2, 2, 0)

    def _entete(self):
        o = self.oled
        o.text("CRT", _COL_X[0], _ENTETE_Y, 1)
        o.text("LNG", _COL_X[1], _ENTETE_Y, 1)
        o.text("DBL", _COL_X[2], _ENTETE_Y, 1)

    def _abrege_geste(self, gestes, nom, largeur):
        """Libelle court d'un geste, ou un tiret s'il n'a pas de macro."""
        actions = (gestes or {}).get(nom)
        if not actions:
            return "-"
        genre, valeur = actions[0]
        if genre in ("combo", "maintien"):
            # D'une combinaison, on montre la derniere touche : dans
            # CTRL+SHIFT+Z, c'est le Z qui distingue la macro des autres.
            # Pour un maintien, c'est le modificateur lui-meme : CTRL, MAJ.
            texte = valeur[-1] if valeur else "?"
        elif genre == "key":
            texte = str(valeur)
        else:
            # Les commandes AutoCAD commencent par un underscore, qui ne
            # sert qu'a forcer la version anglaise : inutile a l'ecran.
            texte = str(valeur).lstrip("_")
        return texte[:largeur].upper()

    def _ligne_tableau(self, rang, index):
        """Dessine une ligne du tableau. rang = position a l'ecran."""
        o = self.oled
        y = _LIGNE_Y[rang]
        label, gestes = self.macros[index]
        surligne = (index == self.surbrillance)

        if surligne:
            o.fill_rect(0, y - 1, 128, 9, 1)
        fond, encre = (1, 0) if surligne else (0, 1)

        o.text(str(index + 1), 0, y, encre)
        # Colonne 1 : le libelle de la touche, plus lisible que la macro
        # elle-meme ("MATCH" parle mieux que "MATC" de "_MATCHPROP").
        o.text(label[:_COL_LARGEUR[0]].upper(), _COL_X[0], y, encre)
        o.text(self._abrege_geste(gestes, "long", _COL_LARGEUR[1]),
               _COL_X[1], y, encre)
        o.text(self._abrege_geste(gestes, "double", _COL_LARGEUR[2]),
               _COL_X[2], y, encre)

    def _zone_document(self):
        """Ou commence le nom du fichier, et quelle largeur lui reste."""
        depart = 2
        if self.doc_abrege:
            depart = 2 + len(self.doc_abrege) * 8 + 5
        return depart, max(0, 128 - depart - 2)

    def _dessiner_bas(self):
        """Redessine UNIQUEMENT la derniere ligne (page 7).

        Elle change souvent a cause du defilement ; la redessiner seule
        divise par huit le trafic I2C.
        """
        o = self.oled
        o.fill_rect(0, 56, 128, 8, 0)
        if not self.doc_nom and not self.doc_abrege:
            return
        depart, _ = self._zone_document()
        if self.doc_nom:
            # framebuf decoupe tout seul ce qui depasse de l'ecran : on peut
            # donc dessiner a une abscisse negative, le debut sort par la
            # gauche. C'est tout le principe du defilement.
            o.text(self.doc_nom, depart - self._defil_x, _BAS_Y + 1, 1)
        if self.doc_abrege:
            # On efface ce que le nom a deborde sur la zone reservee, puis
            # on ecrit l'abreviation par-dessus : elle reste toujours lisible.
            o.fill_rect(0, 56, depart - 2, 8, 0)
            o.text(self.doc_abrege, 2, _BAS_Y + 1, 1)

    def _vue_principale(self):
        o = self.oled
        o.fill(0)
        self._bandeau()
        self._entete()
        for rang in range(_LIGNES_VISIBLES):
            index = self.fenetre + rang
            if index < len(self.macros):
                self._ligne_tableau(rang, index)
        o.hline(0, _SEPARATEUR_Y, 128, 1)
        self._dessiner_bas()

    def _ecrire_grand(self, texte, y0, echelle):
        """Ecrit un texte centre, en police 8x8 agrandie 'echelle' fois.

        MicroPython ne fournit qu'une police 8x8. Pour l'agrandir on dessine
        le texte dans une petite image en memoire, puis on recopie chaque
        pixel sous forme d'un carre de echelle x echelle sur l'ecran.
        """
        import framebuf
        o = self.oled
        largeur = len(texte) * 8
        tampon = framebuf.FrameBuffer(bytearray(128), 128, 8,
                                      framebuf.MONO_HLSB)
        tampon.text(texte, 0, 0, 1)
        x0 = max(0, (128 - largeur * echelle) // 2)
        for x in range(min(128, largeur)):
            for y in range(8):
                if tampon.pixel(x, y):
                    o.fill_rect(x0 + x * echelle, y0 + y * echelle,
                                echelle, echelle, 1)

    def _texte_double(self, texte):
        """Un texte seul, aussi gros que possible, au milieu de l'ecran."""
        self.oled.fill(0)
        echelle = 2 if len(texte) <= 8 else 1
        self._ecrire_grand(texte, (64 - 8 * echelle) // 2, echelle)

    def _deux_lignes(self, haut, bas):
        """Le nom de la combinaison en gros, son libelle juste dessous."""
        o = self.oled
        o.fill(0)
        echelle = 2 if len(haut) <= 8 else 1
        self._ecrire_grand(haut, 24 - 4 * echelle, echelle)
        o.text(bas, max(0, (128 - len(bas) * 8) // 2), 44, 1)

    # ==================================================================
    # Rafraichissements
    # ==================================================================
    def _redessiner(self):
        if not self.oled or self.splash_until is not None:
            return
        try:
            self._vue_principale()
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def _rafraichir_bas(self):
        """Redessine la derniere ligne et ne reenvoie que sa page."""
        if not self.oled or self.splash_until is not None:
            return
        try:
            self._dessiner_bas()
            # 8 = aucun envoi en cours. On ne se glisse dans la file que si
            # un rafraichissement complet n'est pas deja en route, sinon on
            # lui ferait sauter des pages.
            if self.pending_page >= 8:
                self.pending_page = 7
        except Exception as exc:
            self.disable(exc)

    # ==================================================================
    # API publique
    # ==================================================================
    def message(self, *lignes):
        """Quelques lignes de texte brut : SAFE MODE, erreurs, diagnostic."""
        if not self.oled:
            return
        try:
            self.reveiller(ticks_ms())
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
        """Ecran du mode configuration : tout pour se connecter."""
        if not self.oled:
            return
        try:
            self.reveiller(ticks_ms())
            o = self.oled
            o.fill(0)
            self.titre, self.etat = "MODE CONFIG", "WIFI"
            self._bandeau()
            o.text("Reseau :", 2, 15, 1)
            o.text(str(ssid)[:16], 2, 25, 1)
            o.text("Cle :", 2, 36, 1)
            o.text(str(mot_de_passe)[:16], 2, 46, 1)
            o.hline(0, _SEPARATEUR_Y, 128, 1)
            o.text(str(adresse)[:16], 2, _BAS_Y + 1, 1)
            self.splash_until = None
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def set_etat(self, etat):
        """Petit texte en haut a droite : HID, AUTO, LOCK, ERR..."""
        if etat == self.etat:
            return
        self.etat = etat
        self._redessiner()

    def set_document(self, texte):
        """Ce que le PC nous dit du document ouvert.

        Format recu : "C3D|Projet_A12_Phase2.dwg"
        La partie avant la barre verticale est l'abreviation du logiciel,
        qui reste fixe a gauche. Ce qui suit est le nom du fichier, qui
        defilera doucement s'il est trop long. Sans barre, tout est pris
        pour le nom.
        """
        texte = texte or ""
        if "|" in texte:
            abrege, nom = texte.split("|", 1)
        else:
            abrege, nom = "", texte
        abrege, nom = abrege.strip()[:7], nom.strip()[:48]
        if abrege == self.doc_abrege and nom == self.doc_nom:
            return
        self.doc_abrege, self.doc_nom = abrege, nom

        # De combien faut-il defiler pour voir la fin du nom ?
        _, dispo = self._zone_document()
        self._defil_max = max(0, len(nom) * 8 - dispo)
        self._defil_x = 0
        self._defil_sens = 1
        self._defil_t = ticks_add(ticks_ms(), C.DOC_SCROLL_PAUSE_MS)
        self._rafraichir_bas()

    def profile(self, titre, macros, now, index=0, total=1, splash=False):
        """Affiche un profil. splash=True montre d'abord son nom en gros."""
        self.titre = titre
        self.macros = list(macros)
        self.fenetre = 0
        self.surbrillance = -1
        self._fenetre_t = ticks_add(now, C.TABLE_SCROLL_MS)
        if not self.oled:
            return
        try:
            self.reveiller(now)
            if splash:
                self._texte_double(titre[:8])
                self.splash_until = ticks_add(now, C.PROFILE_SPLASH_MS)
            else:
                self.splash_until = None
                self._vue_principale()
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def flash(self, ligne1, ligne2, now):
        """Prend l'ecran un instant : "B3+B4" en gros, le libelle dessous.

        Une combinaison ne correspond a aucune ligne du tableau : le
        surlignage habituel ne peut donc pas la montrer. On reutilise le
        mecanisme du splash de profil - tick() remet la vue normale tout
        seul a l'echeance, sans rien bloquer dans la boucle principale.
        """
        self.reveiller(now)
        if not self.oled:
            return
        # Sinon on retrouverait, au retour, la touche surlignee par l'appui
        # qui a servi a former la combinaison : trompeur.
        self.surbrillance = -1
        try:
            self._deux_lignes(str(ligne1)[:16], str(ligne2)[:16])
            self.splash_until = ticks_add(now, C.COMBO_FLASH_MS)
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def surligner(self, index, now):
        """La touche vient de servir : on saute dessus et on la surligne.

        C'est le retour visuel immediat : tu vois ce que tu as declenche,
        et du meme coup les deux autres gestes disponibles sur cette touche.
        """
        self.reveiller(now)
        if not self.oled or not (0 <= index < len(self.macros)):
            return
        self.surbrillance = index
        self._surbrillance_t = ticks_add(now, C.HIGHLIGHT_MS)
        # On amene la touche dans la fenetre visible si elle n'y est pas.
        if index < self.fenetre:
            self.fenetre = index
        elif index >= self.fenetre + _LIGNES_VISIBLES:
            self.fenetre = index - _LIGNES_VISIBLES + 1
        # Pas de defilement automatique pendant qu'on regarde la touche.
        self._fenetre_t = ticks_add(now, C.HIGHLIGHT_MS + C.TABLE_SCROLL_MS)
        self._redessiner()

    # ==================================================================
    # Economiseur d'ecran
    # ==================================================================
    def reveiller(self, now):
        """A appeler des qu'une touche est actionnee."""
        self._activite = now
        if self._veille == _VEILLE_NORMALE or not self.oled:
            return
        try:
            if self._veille == _VEILLE_ETEINTE:
                self.oled.sleep(False)
            self.oled.contrast(C.OLED_CONTRAST)
            self._veille = _VEILLE_NORMALE
            self.pending_page = 0        # l'image doit etre reenvoyee
        except Exception as exc:
            self.disable(exc)

    def _service_veille(self, now):
        if not self.oled:
            return
        inactif = ticks_diff(now, self._activite)
        try:
            if self._veille == _VEILLE_NORMALE and inactif > C.SCREEN_DIM_MS:
                self.oled.contrast(C.SCREEN_DIM_CONTRAST)
                self._veille = _VEILLE_ATTENUEE
            elif self._veille == _VEILLE_ATTENUEE and inactif > C.SCREEN_OFF_MS:
                self.oled.sleep(True)
                self._veille = _VEILLE_ETEINTE
        except Exception as exc:
            self.disable(exc)

    # ==================================================================
    # A appeler a chaque tour de boucle
    # ==================================================================
    def tick(self, now):
        if not self.oled:
            return

        # --- fin de l'ecran "nom du profil en gros" --------------------
        if self.splash_until is not None and ticks_diff(now, self.splash_until) >= 0:
            self.splash_until = None
            self._redessiner()

        if self._veille == _VEILLE_ETEINTE:
            return          # ecran eteint : plus rien a animer ni a envoyer

        if self.splash_until is None:
            # --- fin du surlignage ------------------------------------
            if (self.surbrillance >= 0
                    and ticks_diff(now, self._surbrillance_t) >= 0):
                self.surbrillance = -1
                self._redessiner()

            # --- defilement automatique du tableau --------------------
            elif (len(self.macros) > _LIGNES_VISIBLES
                    and ticks_diff(now, self._fenetre_t) >= 0):
                maximum = len(self.macros) - _LIGNES_VISIBLES
                self.fenetre = 0 if self.fenetre >= maximum else self.fenetre + 1
                self._fenetre_t = ticks_add(now, C.TABLE_SCROLL_MS)
                self._redessiner()

            # --- defilement du nom de fichier -------------------------
            elif self._defil_max > 0 and ticks_diff(now, self._defil_t) >= 0:
                self._defil_x += self._defil_sens
                if self._defil_x >= self._defil_max:
                    self._defil_x = self._defil_max
                    self._defil_sens = -1
                    self._defil_t = ticks_add(now, C.DOC_SCROLL_PAUSE_MS)
                elif self._defil_x <= 0:
                    self._defil_x = 0
                    self._defil_sens = 1
                    self._defil_t = ticks_add(now, C.DOC_SCROLL_PAUSE_MS)
                else:
                    self._defil_t = ticks_add(now, C.DOC_SCROLL_MS)
                self._rafraichir_bas()

        self._service_veille(now)

        # --- envoi d'AU PLUS une page a l'ecran ------------------------
        if self.pending_page >= 8:
            return
        try:
            page = self.pending_page
            self.oled.write_cmd(0xB0 | page)   # choisir la bande n° page
            self.oled.write_cmd(0x02)          # colonne de depart, poids faibles
            self.oled.write_cmd(0x10)          # colonne de depart, poids forts
            #        ^ 0x02 = le decalage de 2 colonnes propre au SH1106
            self.oled.write_data(
                self.oled.displaybuf[page * 128:(page + 1) * 128])
            self.pending_page += 1
        except Exception as exc:
            # Un ecran arrache en cours de route ne doit pas arreter le clavier.
            self.disable(exc)

    def flush_startup(self):
        """Envoie l'image entiere d'un coup.

        Reserve aux moments ou l'on peut se permettre d'attendre : avant que
        les touches ne deviennent actives, en SAFE MODE, en mode config.
        """
        for _ in range(9):
            self.tick(ticks_ms())
