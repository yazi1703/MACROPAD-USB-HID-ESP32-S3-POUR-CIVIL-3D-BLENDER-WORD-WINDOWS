# -*- coding: utf-8 -*-
"""Tests du compagnon Windows (pc/macropad_auto.py), sur PC.

On ne teste pas les appels a l'API Windows ni le port serie : on teste la
logique pure, celle qui decide quel profil activer, quel abrege afficher
et quel nom de document envoyer. C'est la partie ou une erreur passerait
inapercue.
"""

import os
import pathlib
import sys
import tempfile
import unittest

RACINE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "pc"))

import macropad_auto as MA          # noqa: E402


class NomDeDocument(unittest.TestCase):

    def test_titres_windows_classiques(self):
        cas = [
            ("Projet_A12.dwg - Autodesk Civil 3D 2024", "Projet_A12.dwg"),
            ("Rapport.docx - Word", "Rapport.docx"),
            ("Blender", "Blender"),
            ("*Sans titre 1 - Bloc-notes", "Sans titre 1"),
            ("", ""),
        ]
        for titre, attendu in cas:
            self.assertEqual(MA.nom_document(titre, "x.exe"), attendu, titre)

    def test_titres_entre_crochets(self):
        # Blender et l'AutoCAD classique mettent le fichier entre crochets.
        self.assertEqual(
            MA.nom_document("Blender* [C:\\Travail\\maquette.blend]",
                            "blender.exe"),
            "maquette.blend")
        self.assertEqual(
            MA.nom_document("Autodesk Civil 3D - [Plan_masse.dwg]", "acad.exe"),
            "Plan_masse.dwg")

    def test_chemin_complet_reduit_au_nom_de_fichier(self):
        # L'ecran n'a pas la place pour un chemin ; on garde la fin.
        self.assertEqual(
            MA.nom_document("C:/Users/yazid/Documents/leve.dwg - Civil 3D",
                            "acad.exe"),
            "leve.dwg")

    def test_coupe_a_ce_que_l_ecran_retient(self):
        # L'ecran fait defiler le nom, mais n'en garde que 48 caracteres :
        # inutile d'envoyer davantage.
        long_titre = ("UnNomDeFichierVraimentTresTresTresTresTresTresTresLong"
                      ".dwg - Civil 3D")
        resultat = MA.nom_document(long_titre, "acad.exe")
        self.assertEqual(len(resultat), MA.DOC_MAX)
        self.assertTrue(resultat.startswith("UnNomDeFichier"))


class TableDeSecours(unittest.TestCase):
    """macropad_apps.txt : la source utilisee quand la carte se tait."""

    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.chemin = os.path.join(self.dossier, "apps.txt")

    def _ecrire(self, contenu):
        with open(self.chemin, "w", encoding="utf-8") as fichier:
            fichier.write(contenu)

    def test_fichier_cree_avec_les_valeurs_par_defaut(self):
        table = MA.TableApplications(self.chemin)
        self.assertTrue(os.path.exists(self.chemin))
        self.assertEqual(table.regle("acad.exe"), ("CIVIL3D", "C3D"))
        self.assertEqual(table.regle("blender.exe"), ("BLENDER", "Blender"))
        self.assertEqual(table.regle("winword.exe"), ("WORD", "Wrd"))
        # Tout le reste bascule sur la ligne "tout le reste".
        self.assertEqual(table.regle("chrome.exe"), ("WINDOWS", "Win"))
        self.assertEqual(table.regle(""), ("WINDOWS", "Win"))

    def test_abrege_deduit_quand_le_champ_manque(self):
        # Ancien format a deux champs : on reprend le nom du profil, coupe.
        self._ecrire("acad.exe = CIVIL3D\n* = WINDOWS\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(table.regle("acad.exe"), ("CIVIL3D", "CIVIL3D"))
        self.assertEqual(table.regle("autre.exe"), ("WINDOWS", "WINDOWS"))

    def test_abrege_coupe_a_sept_caracteres(self):
        self._ecrire("qgis-bin.exe = QGIS = TropLongPourLEcran\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(table.abrege("qgis-bin.exe"), "TropLon")
        self.assertEqual(len(table.abrege("qgis-bin.exe")), MA.ABREGE_MAX)

    def test_insensible_a_la_casse(self):
        self._ecrire("ACAD.EXE = civil3d = C3D\n* = WINDOWS = Win\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(table.profil("acad.exe"), "CIVIL3D")
        self.assertEqual(table.profil("AcAd.ExE"), "CIVIL3D")

    def test_commentaires_et_lignes_vides_ignores(self):
        self._ecrire("# un commentaire\n\n  \nqgis-bin.exe=QGIS=Qgis\n"
                     "* = WINDOWS = Win\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(table.regle("qgis-bin.exe"), ("QGIS", "Qgis"))
        self.assertEqual(len(table.regles), 1)

    def test_relecture_a_chaud(self):
        self._ecrire("acad.exe = CIVIL3D = C3D\n* = WINDOWS = Win\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(table.profil("excel.exe"), "WINDOWS")

        # L'utilisateur ajoute une ligne pendant que le script tourne.
        self._ecrire("acad.exe = CIVIL3D = C3D\nexcel.exe = WORD = Xls\n"
                     "* = WINDOWS = Win\n")
        table._date = 0                 # simule un horodatage different
        table.recharger()
        self.assertEqual(table.regle("excel.exe"), ("WORD", "Xls"))

    def test_fichier_illisible_ne_plante_pas(self):
        self._ecrire("n importe quoi sans signe egal\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(table.regle("acad.exe"), ("WINDOWS", "Win"))  # repli

    def test_ligne_sans_profil_ignoree(self):
        self._ecrire("machin.exe =\nacad.exe = CIVIL3D = C3D\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(len(table.regles), 1)
        self.assertEqual(table.profil("machin.exe"), "WINDOWS")


class _MacropadFactice:
    """Un faux macropad : il rend la configuration qu'on lui a donnee."""

    def __init__(self, config=None, panne=False):
        self.config = config
        self.panne = panne
        self.appels = 0

    def lire_config(self):
        self.appels += 1
        if self.panne:
            raise TimeoutError("le macropad n'a pas repondu")
        return self.config


class TableLueSurLaCarte(unittest.TestCase):
    """La carte est la source normale ; le fichier n'est que le secours."""

    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.chemin = os.path.join(self.dossier, "apps.txt")
        with open(self.chemin, "w", encoding="utf-8") as fichier:
            fichier.write("acad.exe = CIVIL3D = C3D\n* = WINDOWS = Win\n")
        self.table = MA.TableApplications(self.chemin)

    @staticmethod
    def _config(liste, repli=None):
        return {"apps": {"liste": liste,
                         "repli": repli or {"profil": "WINDOWS",
                                            "abrege": "Win"}}}

    def test_la_carte_remplace_le_fichier(self):
        carte = _MacropadFactice(self._config(
            [{"exe": "blender.exe", "profil": "BLENDER", "abrege": "Blender"}],
            {"profil": "BUREAU", "abrege": "Bur"}))
        self.assertTrue(self.table.synchroniser(carte))
        self.assertEqual(self.table.regle("blender.exe"),
                         ("BLENDER", "Blender"))
        # acad.exe existe dans le fichier, mais la carte ne le connait pas :
        # on ne melange pas les deux sources, donc c'est le repli.
        self.assertEqual(self.table.regle("acad.exe"), ("BUREAU", "Bur"))
        self.assertEqual(self.table.source, "macropad")

    def test_table_vide_sur_la_carte_laisse_le_fichier_travailler(self):
        carte = _MacropadFactice(self._config([]))
        self.assertTrue(self.table.synchroniser(carte))
        self.assertEqual(self.table.regle("acad.exe"), ("CIVIL3D", "C3D"))
        self.assertEqual(self.table.source, "apps.txt")

    def test_carte_muette_garde_le_fichier(self):
        carte = _MacropadFactice(panne=True)
        self.assertFalse(self.table.synchroniser(carte))
        self.assertEqual(self.table.regle("acad.exe"), ("CIVIL3D", "C3D"))

    def test_carte_muette_apres_une_lecture_reussie_garde_la_table(self):
        bonne = _MacropadFactice(self._config(
            [{"exe": "blender.exe", "profil": "BLENDER", "abrege": "Blender"}]))
        self.table.synchroniser(bonne)
        self.assertFalse(self.table.synchroniser(_MacropadFactice(panne=True)))
        self.assertEqual(self.table.regle("blender.exe"),
                         ("BLENDER", "Blender"))

    def test_lignes_incompletes_ignorees(self):
        carte = _MacropadFactice(self._config([
            {"exe": "", "profil": "CIVIL3D", "abrege": "C3D"},
            {"exe": "vide.exe", "profil": "", "abrege": ""},
            {"exe": "WinWord.EXE", "profil": "word", "abrege": ""},
        ]))
        self.table.synchroniser(carte)
        self.assertEqual(len(self.table.regles_carte), 1)
        # Casse normalisee, et abrege deduit du profil quand il manque.
        self.assertEqual(self.table.regle("winword.exe"), ("WORD", "WORD"))

    def test_une_table_identique_ne_change_rien(self):
        config = self._config(
            [{"exe": "acad.exe", "profil": "CIVIL3D", "abrege": "C3D"}])
        self.assertTrue(self.table.depuis_la_carte(config["apps"]))
        self.assertFalse(self.table.depuis_la_carte(config["apps"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
