# -*- coding: utf-8 -*-
"""
link.py - Le dialogue avec le PC par le port serie USB.

=====================================================================
A QUOI CA SERT
=====================================================================
Ton macropad expose DEUX choses sur le meme cable USB :

  * un clavier HID, qui tape dans la fenetre active ;
  * un port serie (celui du REPL), jusqu'ici inutilise par le firmware.

Ce module se sert de ce second canal pour parler avec un petit programme
qui tourne sur le PC (tools/macropad_auto.py). Ce programme :

  * regarde quelle application est au premier plan et le dit au macropad,
    qui change alors de profil tout seul ;
  * envoie le nom du document ouvert, que l'ecran affiche ;
  * sert une page de configuration sur http://127.0.0.1:8765, et transmet
    tes modifications au macropad, qui les applique SANS redemarrer.

=====================================================================
POURQUOI LA LECTURE NE BLOQUE JAMAIS
=====================================================================
Lire une ligne sur un port serie, normalement, ca attend. Si on faisait
cela dans la boucle principale, le macropad se figerait des que le PC ne
dit rien - c'est-a-dire tout le temps.

On utilise donc select.poll() qui repond "y a-t-il un caractere pret ?"
sans jamais attendre, et on lit caractere par caractere. Deux precautions :

  * on lit AU PLUS 256 caracteres par tour de boucle, pour qu'un gros
    envoi de configuration (2 a 3 ko) s'etale sur quelques tours au lieu
    de bloquer les touches pendant 40 ms ;
  * on ne se sert jamais de readline(), qui attendrait le passage a la
    ligne meme si le message est incomplet.

=====================================================================
LE PROTOCOLE, EN CLAIR
=====================================================================
Une commande par ligne. Du PC vers le macropad :

  P:CIVIL3D          le logiciel actif correspond a ce profil
  T:Projet_A12.dwg   nom du document a afficher (vide = efface)
  ?VER               demande l'etat du macropad
  ?CFG               demande la configuration complete
  !CFGBEGIN          debut d'un envoi de configuration
  !C:<morceau>       un morceau de JSON (on decoupe pour ne pas saturer)
  !CFGEND            fin de l'envoi : on verifie, on enregistre, on applique
  !RELOAD            relire profils.json sans redemarrer

Du macropad vers le PC, toujours prefixe par # pour que le script les
distingue des messages de debogage ordinaires :

  #VER:...  #CFGBEGIN  #C:<morceau>  #CFGEND  #OK:...  #KO:<raison>

Aucun caractere de controle n'est utilise : Ctrl-C continue donc
d'interrompre le programme normalement, tu ne perds pas cette porte de
sortie.
"""

import json

import config as C
import store

# Evenements rendus a main.py
EVT_PROFIL = "profil"        # le PC demande un profil
EVT_DOCUMENT = "document"    # nom du document a afficher
EVT_RECHARGER = "recharger"  # la configuration a change, il faut la relire

_MAX_PAR_TOUR = 256          # caracteres lus au maximum par tour de boucle
_MAX_LIGNE = 512             # au-dela, la ligne est jetee (protection RAM)
_MAX_CONFIG = 8192           # taille maximale d'une configuration recue
_TAILLE_MORCEAU = 180        # taille des morceaux envoyes au PC


class SourceStdin:
    """Lecture non bloquante du port serie (le REPL) sous MicroPython."""

    def __init__(self):
        import select
        import sys
        self._sys = sys
        self._poll = select.poll()
        self._poll.register(sys.stdin, select.POLLIN)

    def lire(self, maximum):
        morceaux = []
        while len(morceaux) < maximum and self._poll.poll(0):
            caractere = self._sys.stdin.read(1)
            if not caractere:
                break
            morceaux.append(caractere)
        return "".join(morceaux)


class Link:
    """Analyse les lignes venant du PC et repond."""

    def __init__(self, nb_touches, source=None, sortie=None, stats=None):
        self.nb_touches = nb_touches
        self.stats = stats            # pour joindre les compteurs d'usage
        self.actif = False
        self.source = source
        self.sortie = sortie or print
        self._tampon = ""        # ligne en cours de reception
        self._config = None      # configuration en cours de reception
        self.dernier_profil = None
        self.document = ""

        if self.source is None:
            try:
                self.source = SourceStdin()
            except Exception as exc:
                print("[link] port serie indisponible :", exc)
                return
        self.actif = True

    # ------------------------------------------------------------------
    def service(self):
        """A appeler a chaque tour de boucle. Retourne une liste d'evenements."""
        if not self.actif:
            return ()
        try:
            recu = self.source.lire(_MAX_PAR_TOUR)
        except Exception as exc:
            print("[link] lecture impossible :", exc)
            self.actif = False
            return ()
        if not recu:
            return ()

        evenements = []
        for caractere in recu:
            if caractere == "\n":
                ligne, self._tampon = self._tampon, ""
                evenement = self._traiter(ligne.strip())
                if evenement:
                    evenements.append(evenement)
            elif caractere != "\r":
                if len(self._tampon) < _MAX_LIGNE:
                    self._tampon += caractere
                else:
                    self._tampon = ""     # ligne aberrante : on la jette
        return evenements

    # ------------------------------------------------------------------
    def _traiter(self, ligne):
        if not ligne:
            return None

        if ligne.startswith("P:"):
            self.dernier_profil = ligne[2:].strip().upper()
            return (EVT_PROFIL, self.dernier_profil)

        if ligne.startswith("T:"):
            self.document = ligne[2:].strip()
            return (EVT_DOCUMENT, self.document)

        if ligne == "?VER":
            self.sortie("#VER:macropad %d touches, layout %s"
                        % (self.nb_touches, C.KEYBOARD_LAYOUT))
            return None

        if ligne == "?CFG":
            self._envoyer_config()
            return None

        if ligne == "!CFGBEGIN":
            self._config = []
            return None

        if ligne.startswith("!C:"):
            if self._config is not None:
                morceau = ligne[3:]
                total = sum(len(m) for m in self._config)
                if total + len(morceau) <= _MAX_CONFIG:
                    self._config.append(morceau)
                else:
                    self._config = None
                    self.sortie("#KO:configuration trop volumineuse")
            return None

        if ligne == "!CFGEND":
            return self._recevoir_config()

        if ligne == "!RELOAD":
            self.sortie("#OK:rechargement")
            return (EVT_RECHARGER, None)

        if ligne == "!ZERO":
            # Remise a zero des compteurs d'usage. remettre_a_zero() efface
            # AUSSI le fichier : sans cela, enregistrer() refuserait d'ecrire
            # une table vide et les anciens chiffres reviendraient au
            # prochain demarrage. Une remise a zero qui ne survit pas au
            # redemarrage n'en est pas une.
            if self.stats is None:
                self.sortie("#KO:compteurs indisponibles")
                return None
            self.stats.remettre_a_zero()
            self.sortie("#OK:compteurs remis a zero")
            return None

        return None

    # ------------------------------------------------------------------
    def _envoyer_config(self):
        """Envoie la configuration au PC, decoupee en morceaux."""
        try:
            texte = json.dumps(store.vers_json(self.nb_touches, self.stats))
        except Exception as exc:
            self.sortie("#KO:lecture impossible : %s" % exc)
            return

        self.sortie("#CFGBEGIN")
        for debut in range(0, len(texte), _TAILLE_MORCEAU):
            self.sortie("#C:" + texte[debut:debut + _TAILLE_MORCEAU])
        self.sortie("#CFGEND")

    def _recevoir_config(self):
        """Verifie et enregistre la configuration recue du PC."""
        if self._config is None:
            self.sortie("#KO:aucun envoi en cours")
            return None
        texte = "".join(self._config)
        self._config = None

        try:
            data = json.loads(texte)
        except Exception as exc:
            self.sortie("#KO:JSON invalide : %s" % exc)
            return None

        # store refuse toute macro qui ne serait pas tapable : impossible
        # d'enregistrer depuis le PC une configuration qui planterait au
        # demarrage suivant.
        ok, raison = store.enregistrer_json(data, self.nb_touches)
        if ok:
            self.sortie("#OK:configuration enregistree")
            return (EVT_RECHARGER, None)
        self.sortie("#KO:" + raison)
        return None
