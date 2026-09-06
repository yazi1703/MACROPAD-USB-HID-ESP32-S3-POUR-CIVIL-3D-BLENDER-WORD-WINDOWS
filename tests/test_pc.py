# -*- coding: utf-8 -*-
"""Tests du compagnon Windows (pc/macropad_auto.py), sur PC.

On ne teste pas les appels a l'API Windows ni le port serie : on teste la
logique pure, celle qui decide quel profil activer et quel nom de document
afficher. C'est la partie ou une erreur passerait inapercue.
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

    def test_tronque_a_la_largeur_de_l_ecran(self):
        # L'ecran n'affiche que 16 caracteres par ligne.
        long_titre = "UnNomDeFichierBeaucoupTropLong.dwg - Civil 3D"
        self.assertLessEqual(len(MA.nom_document(long_titre, "acad.exe")), 16)


class TableDesApplications(unittest.TestCase):

    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.chemin = os.path.join(self.dossier, "apps.txt")

    def _ecrire(self, contenu):
        with open(self.chemin, "w", encoding="utf-8") as fichier:
            fichier.write(contenu)

    def test_fichier_cree_avec_les_valeurs_par_defaut(self):
        table = MA.TableApplications(self.chemin)
        self.assertTrue(os.path.exists(self.chemin))
        self.assertEqual(table.profil("acad.exe"), "CIVIL3D")
        self.assertEqual(table.profil("blender.exe"), "BLENDER")
        self.assertEqual(table.profil("winword.exe"), "WORD")
        # Tout le reste bascule sur le profil de repli.
        self.assertEqual(table.profil("chrome.exe"), "WINDOWS")
        self.assertEqual(table.profil(""), "WINDOWS")

    def test_insensible_a_la_casse(self):
        self._ecrire("ACAD.EXE = CIVIL3D\n* = WINDOWS\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(table.profil("acad.exe"), "CIVIL3D")
        self.assertEqual(table.profil("AcAd.ExE"), "CIVIL3D")

    def test_commentaires_et_lignes_vides_ignores(self):
        self._ecrire("# un commentaire\n\n  \nqgis-bin.exe=QGIS\n* = WINDOWS\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(table.profil("qgis-bin.exe"), "QGIS")
        self.assertEqual(len(table.regles), 1)

    def test_relecture_a_chaud(self):
        self._ecrire("acad.exe = CIVIL3D\n* = WINDOWS\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(table.profil("excel.exe"), "WINDOWS")

        # L'utilisateur ajoute une ligne pendant que le script tourne.
        self._ecrire("acad.exe = CIVIL3D\nexcel.exe = WORD\n* = WINDOWS\n")
        table._date = 0                 # simule un horodatage different
        table.recharger()
        self.assertEqual(table.profil("excel.exe"), "WORD")

    def test_fichier_illisible_ne_plante_pas(self):
        self._ecrire("n importe quoi sans signe egal\n")
        table = MA.TableApplications(self.chemin)
        self.assertEqual(table.profil("acad.exe"), "WINDOWS")   # repli


if __name__ == "__main__":
    unittest.main(verbosity=2)
