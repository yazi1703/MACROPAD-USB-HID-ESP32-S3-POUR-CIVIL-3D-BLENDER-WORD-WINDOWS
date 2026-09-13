# -*- coding: utf-8 -*-
"""Tests du compagnon Windows (pc/macropad_auto.py), sur PC.

On ne teste pas les appels a l'API Windows ni le port serie : on teste la
logique pure, celle qui decide quel profil activer, quel abrege afficher
et quel nom de document envoyer. C'est la partie ou une erreur passerait
inapercue.
"""

import io
import os
import pathlib
import sys
import tempfile
import types
import unittest
import unittest.mock

RACINE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "pc"))

import macropad_auto as MA          # noqa: E402


class RecapitulatifDesCommandes(unittest.TestCase):
    """L'ecran OLED fait 16 caracteres sur 4 lignes visibles.

    Le profil CIVIL3D compte a lui seul 19 entrees. Il n'y a pas de
    reglage a trouver : il manque un facteur cinq. Le recapitulatif
    complet vit donc sur l'ecran du PC, et c'est cette mise en forme -
    pure, sans fenetre ni port serie - que ces tests verifient.
    """

    CONFIG = {
        "gestes": ["court", "long", "double"],
        "profils": {
            "CIVIL3D": {
                "titre": "CIVIL 3D",
                "touches": [
                    {"label": "CTRL",
                     "nom": "Ctrl maintenu, Maj en double",
                     "court": [{"type": "maintien", "valeur": "CTRL"}],
                     "long": [],
                     "double": [{"type": "maintien", "valeur": "MAJ"}]},
                    {"label": "COPIER",
                     "court": [{"type": "combo", "valeur": "CTRL+C"}],
                     "long": [{"type": "text_enter", "valeur": "_PURGE"},
                              {"type": "pause", "valeur": "500"},
                              {"type": "combo", "valeur": "CTRL+S"}],
                     "double": [{"type": "combo", "valeur": "CTRL+V"}]},
                    {"label": "VIDE",
                     "court": [{"type": "none", "valeur": ""}],
                     "long": [], "double": []},
                ],
                "combos": [
                    {"touches": [5, 6], "label": "VUE PREC.",
                     "nom": "Vue precedente",
                     "actions": [{"type": "text_enter",
                                  "valeur": "MPVIEWPREV"}]},
                ],
            },
        },
        "esc": {"court": [{"type": "key", "valeur": "ESC"}],
                "maintien": [{"type": "combo", "valeur": "CTRL+Z"}]},
    }

    def _lignes(self):
        return MA.lignes_du_profil(self.CONFIG, "CIVIL3D")

    def test_chaque_touche_a_son_en_tete_puis_ses_gestes(self):
        """Une ligne d'en-tete par touche : numero, libelle court, nom
        complet. Les gestes viennent dessous, sans repeter le numero."""
        lignes = self._lignes()
        self.assertIn(("B1", "CTRL", "", "Ctrl maintenu, Maj en double"),
                      lignes)
        self.assertIn(("", "", "appui court", "maintenir CTRL"), lignes)
        self.assertIn(("", "", "double appui", "maintenir MAJ"), lignes)
        self.assertIn(("B2", "COPIER", "", ""), lignes)
        self.assertIn(("", "", "appui court", "CTRL+C"), lignes)

    def test_une_suite_d_etapes_se_lit_d_un_trait(self):
        """Le cas qui justifie ce recapitulatif : une macro en trois temps
        est illisible sur un ecran de 16 caracteres."""
        lignes = self._lignes()
        self.assertIn(
            ("", "", "appui long",
             "taper _PURGE puis Entree, puis attendre 500 ms, puis CTRL+S"),
            lignes)

    def test_le_nom_de_la_touche_ne_se_repete_pas(self):
        """L'oeil doit retrouver les touches d'un coup : le numero et le
        libelle ne figurent que sur la PREMIERE ligne de chaque touche."""
        lignes = self._lignes()
        b2 = [i for i, l in enumerate(lignes) if l[0] == "B2"]
        self.assertEqual(len(b2), 1)
        # Les trois lignes suivantes appartiennent a B2 et sont anonymes.
        for decalage in (1, 2, 3):
            self.assertEqual(lignes[b2[0] + decalage][0], "")

    def test_un_geste_vide_ne_prend_pas_de_ligne(self):
        lignes = self._lignes()
        self.assertNotIn("VIDE", [l[1] for l in lignes])

    def test_les_combinaisons_et_ESC_y_sont_aussi(self):
        """Un recapitulatif qui les oublierait ne servirait a rien : ce
        sont justement celles qu'on ne retient pas."""
        lignes = self._lignes()
        self.assertIn(("B5+B6", "VUE PREC.", "", "Vue precedente"), lignes)
        self.assertIn(("", "", "ensemble", "taper MPVIEWPREV puis Entree"),
                      lignes)
        self.assertIn(("ESC", "", "appui court", "ESC"), lignes)
        self.assertIn(("", "", "maintenu", "CTRL+Z"), lignes)

    def test_un_profil_inconnu_ne_garde_que_ce_qui_est_global(self):
        """ESC ne fait partie d'aucun profil : il fonctionne dans TOUS.

        Il doit donc figurer dans chaque recapitulatif, meme celui d'un
        profil qu'on ne connait pas.
        """
        lignes = MA.lignes_du_profil(self.CONFIG, "INEXISTANT")
        self.assertEqual([l[0] for l in lignes], ["ESC", ""])

    def test_une_configuration_absente_ne_plante_pas(self):
        self.assertEqual(MA.lignes_du_profil(None, "CIVIL3D"), [])
        self.assertEqual(MA.lignes_du_profil({}, "CIVIL3D"), [])

    def test_l_ancienne_forme_a_une_seule_action_se_lit_encore(self):
        """Un profils.json ecrit avant les suites d'etapes range un SEUL
        objet par geste. Le recapitulatif ne doit pas s'y casser."""
        self.assertEqual(
            MA.texte_actions({"type": "combo", "valeur": "CTRL+C"}), "CTRL+C")

    def test_le_panneau_absent_ne_casse_rien(self):
        """Sans tkinter, le compagnon doit continuer comme avant.

        Le panneau est un confort : il n'a pas le droit d'etre la raison
        d'une panne.
        """
        panneau = MA.Panneau(5.0)
        vrai = sys.modules.pop("tkinter", None)
        sys.modules["tkinter"] = None          # provoque l'ImportError
        try:
            sortie = io.StringIO()
            with unittest.mock.patch("sys.stdout", sortie):
                self.assertFalse(panneau.demarrer())
            self.assertIn("indisponible", sortie.getvalue())
        finally:
            if vrai is not None:
                sys.modules["tkinter"] = vrai
            else:
                sys.modules.pop("tkinter", None)
        # Et les appels suivants ne font rien, sans lever.
        panneau.montrer("CIVIL3D", [])
        panneau.fermer()
        self.assertTrue(panneau.file.empty())


class LePanneauNeDoitPasFausserLaDetection(unittest.TestCase):
    """LE piege de ce panneau, et la raison de la garde au niveau du PID.

    Le recapitulatif est une fenetre DE CE MEME PROGRAMME. S'il passait au
    premier plan - un clic dessus pour l'epingler, par exemple - la
    detection croirait que tu viens de changer de logiciel et basculerait
    le profil. Regarder ses propres raccourcis les changerait : absurde.

    La fenetre est donc sans barre de titre et ne prend jamais le focus ;
    et si Windows la donnait quand meme au premier plan, lire() la
    reconnait a son PID et rend (None, None), que la boucle traite comme
    « ne touche a rien ».
    """

    class _Ref:
        def __init__(self, cible):
            self.cible = cible

    class _Tampon:
        def __init__(self):
            self.value = ""

    def _fenetre(self, pid, titre="Civil 3D - Projet.dwg"):
        """Une FenetreActive branchee sur un faux Windows."""
        essai = self

        class FauxCtypes:
            @staticmethod
            def byref(objet):
                return essai._Ref(objet)

            @staticmethod
            def create_unicode_buffer(taille):
                tampon = essai._Tampon()
                tampon.value = titre
                return tampon

        class FauxDWORD:
            def __init__(self):
                self.value = 0

        class FauxWintypes:
            DWORD = FauxDWORD

        class FauxUser32:
            @staticmethod
            def GetForegroundWindow():
                return 4321

            @staticmethod
            def GetWindowThreadProcessId(poignee, reference):
                reference.cible.value = pid
                return 1

            @staticmethod
            def GetWindowTextLengthW(poignee):
                return len(titre)

            @staticmethod
            def GetWindowTextW(poignee, tampon, taille):
                return len(titre)

        class FauxKernel32:
            @staticmethod
            def OpenProcess(*a):
                return 0            # on s'arrete la : le titre suffit

        objet = MA.FenetreActive.__new__(MA.FenetreActive)
        objet.disponible = True
        objet.ctypes = FauxCtypes
        objet.wintypes = FauxWintypes
        objet.user32 = FauxUser32
        objet.kernel32 = FauxKernel32
        return objet

    def test_notre_propre_fenetre_est_reconnue(self):
        """Le panneau au premier plan ne doit RIEN changer."""
        programme, titre = self._fenetre(os.getpid()).lire()
        self.assertIsNone(programme)
        self.assertIsNone(titre)

    def test_une_vraie_fenetre_est_lue_normalement(self):
        """Et le cas courant continue de marcher, evidemment."""
        programme, titre = self._fenetre(os.getpid() + 1).lire()
        self.assertIsNotNone(programme)
        self.assertEqual(titre, "Civil 3D - Projet.dwg")

    def test_None_et_chaine_vide_ne_veulent_pas_dire_la_meme_chose(self):
        """« aucune fenetre » et « la notre » appellent deux reactions
        differentes : la premiere bascule sur le profil de repli, la
        seconde ne doit rien toucher du tout."""
        class SansFenetre(MA.FenetreActive):
            def __init__(self):
                self.disponible = False

        self.assertEqual(SansFenetre().lire(), ("", ""))
        self.assertEqual(self._fenetre(os.getpid()).lire(), (None, None))


class PourquoiLeMacropadEstInjoignable(unittest.TestCase):
    """La page web doit dire POURQUOI, pas seulement QUE.

    Ne du cas reel : la page affichait "Lecture impossible : macropad non
    connecte", point. Trois causes tres differentes se cachent derriere -
    aucun port Espressif, port occupe par Thonny, pyserial absent - et la
    seule qui soit vraie etait dans la console du compagnon, une fenetre
    qu'on ne regarde pas quand on est dans le navigateur.
    """

    def _lien_sans_carte(self):
        """Un Macropad construit sans toucher au port serie."""
        import threading
        lien = MA.Macropad.__new__(MA.Macropad)
        lien.simuler = False
        lien.serie = None
        lien.port_demande = None
        lien.port = None
        lien.verrou = threading.Lock()
        lien.generation = 0
        lien._absence_signalee = False
        lien.raison_absence = "pas encore de tentative de connexion"
        return lien

    @staticmethod
    def _faux_serial(ouvrir=None):
        """Un module serial factice : pyserial n'est pas installe ici.

        Sans lui, assurer() s'arreterait a l'import et on ne testerait
        jamais les branches suivantes.
        """
        faux = types.ModuleType("serial")
        faux.Serial = ouvrir or (lambda *a, **k: None)
        return faux

    def test_aucun_port_espressif_le_dit(self):
        lien = self._lien_sans_carte()
        with unittest.mock.patch.dict(sys.modules,
                                      {"serial": self._faux_serial()}):
            with unittest.mock.patch.object(MA.Macropad, "trouver_port",
                                            staticmethod(lambda: None)):
                with self.assertRaises(IOError) as capture:
                    lien.lire_config()
        message = str(capture.exception)
        self.assertIn("macropad non connecte", message)
        self.assertIn("0x303A", message)

    def test_port_occupe_le_dit_avec_le_nom_du_port(self):
        """Le cas Thonny : le port existe, mais il est pris."""
        lien = self._lien_sans_carte()
        def refuser(port, vitesse, timeout=None):
            raise OSError("Acces refuse")
        with unittest.mock.patch.dict(
                sys.modules, {"serial": self._faux_serial(refuser)}):
            with unittest.mock.patch.object(MA.Macropad, "trouver_port",
                                            staticmethod(lambda: "COM7")):
                ok, raison = lien.ecrire_config({})
        self.assertFalse(ok)
        self.assertIn("COM7", raison)
        self.assertIn("Acces refuse", raison)

    def test_pyserial_absent_le_dit(self):
        lien = self._lien_sans_carte()
        vrai = sys.modules.pop("serial", None)
        sys.modules["serial"] = None       # provoque l'ImportError
        try:
            with self.assertRaises(IOError) as capture:
                lien.lire_config()
        finally:
            if vrai is not None:
                sys.modules["serial"] = vrai
            else:
                sys.modules.pop("serial", None)
        self.assertIn("pyserial", str(capture.exception))

    def test_la_raison_survit_au_silence_de_la_console(self):
        """La console ne se repete pas ; la page, elle, redemande a chaque fois."""
        lien = self._lien_sans_carte()
        with unittest.mock.patch.dict(sys.modules,
                                      {"serial": self._faux_serial()}):
            with unittest.mock.patch.object(MA.Macropad, "trouver_port",
                                            staticmethod(lambda: None)):
                for _ in range(3):
                    lien.assurer()
        # _signaler_absence n'a imprime qu'une fois, mais la raison est
        # toujours disponible pour la page.
        self.assertTrue(lien._absence_signalee)
        self.assertIn("0x303A", lien._sans_carte())

    def test_un_debranchement_en_cours_de_route_est_nomme(self):
        lien = self._lien_sans_carte()
        lien._perdu(OSError("device disconnected"))
        self.assertIn("debranche", lien._sans_carte())
        self.assertIn("device disconnected", lien._sans_carte())


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


class DemarrageAutomatiqueWindows(unittest.TestCase):
    """Le raccourci du dossier de demarrage : on teste ce qui est verifiable
    sans Windows, c'est-a-dire les chemins et le script PowerShell produit."""

    def setUp(self):
        import demarrage_windows
        self.DW = demarrage_windows

    def test_dossier_de_demarrage(self):
        env = {"APPDATA": os.path.join("C:\\Users", "yazid", "AppData",
                                       "Roaming")}
        dossier = self.DW.dossier_demarrage(env)
        self.assertEqual(
            dossier,
            os.path.join(env["APPDATA"], "Microsoft", "Windows", "Start Menu",
                         "Programs", "Startup"))
        self.assertTrue(self.DW.chemin_raccourci(env).endswith("Macropad.lnk"))

    def test_sans_appdata_message_clair(self):
        with self.assertRaises(RuntimeError):
            self.DW.dossier_demarrage({})

    def test_apostrophes_doublees_pas_les_antislash(self):
        # PowerShell : dans une chaine entre apostrophes, seul ' s'echappe.
        # Un antislash doit rester tel quel, sinon les chemins Windows
        # seraient massacres.
        self.assertEqual(self.DW._texte_ps("C:\\Users\\yazid"),
                         "'C:\\Users\\yazid'")
        self.assertEqual(self.DW._texte_ps("D:\\Dossier d'Yves"),
                         "'D:\\Dossier d''Yves'")

    def test_script_powershell_complet(self):
        script = self.DW.commande_powershell(
            "C:\\Startup\\Macropad.lnk",
            cible="C:\\Projet\\pc\\macropad_auto.bat",
            dossier="C:\\Projet\\pc")
        for morceau in ("CreateShortcut('C:\\Startup\\Macropad.lnk')",
                        "$r.TargetPath = 'C:\\Projet\\pc\\macropad_auto.bat'",
                        "$r.Arguments = '--journal'",
                        "$r.WorkingDirectory = 'C:\\Projet\\pc'",
                        "$r.WindowStyle = 7",
                        "$r.Save()"):
            self.assertIn(morceau, script)

    def test_hors_windows_ne_touche_a_rien(self):
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()) as sortie:
            code = self.DW.main(["--installer"])
        self.assertEqual(code, 1)
        self.assertIn("Windows", sortie.getvalue())


class JournalDuCompagnon(unittest.TestCase):
    """Sans console visible, le journal est le seul temoin."""

    def test_ecrit_dans_les_deux_sorties(self):
        console, fichier = io.StringIO(), io.StringIO()
        double = MA._Double(console, fichier)
        double.write("bonjour")
        double.flush()
        self.assertEqual(console.getvalue(), "bonjour")
        self.assertEqual(fichier.getvalue(), "bonjour")

    def test_une_console_absente_ne_casse_rien(self):
        # Lance sans console (pythonw), sys.__stdout__ peut etre None ou
        # inutilisable : le journal doit continuer a fonctionner.
        class Cassee:
            def write(self, texte):
                raise ValueError("pas de console")

            def flush(self):
                raise ValueError("pas de console")

        fichier = io.StringIO()
        double = MA._Double(Cassee(), fichier)
        double.write("toujours la")
        double.flush()
        self.assertEqual(fichier.getvalue(), "toujours la")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class AgendaDuJourCotePC(unittest.TestCase):
    """Ce que le compagnon lit dans le fichier, et ce qu'il en envoie.

    Fonctions PURES : ni fichier, ni port serie, ni horloge. Ce sont
    elles qui portent les deux pieges de cette fonctionnalite - le fuseau
    horaire et les accents - et un piege muet est le pire genre.
    """

    JOUR = __import__("datetime").date(2026, 9, 13)

    def _du_jour(self, donnees):
        return MA.evenements_du_jour(donnees, self.JOUR)

    # --- le fuseau horaire ------------------------------------------
    def test_une_heure_en_UTC_est_ramenee_a_l_heure_locale(self):
        """LE PIEGE PRINCIPAL, et il est silencieux.

        Un calendrier d'entreprise donne tres souvent ses heures en UTC.
        Les prendre telles quelles decalerait TOUT l'agenda d'une ou deux
        heures selon la saison, sans que rien ne le signale : on arriverait
        en retard en croyant etre en avance.
        """
        import datetime
        utc = MA.instant("2026-09-13T14:00:00Z", self.JOUR)
        attendu = datetime.datetime(2026, 9, 13, 14, 0,
                                    tzinfo=datetime.timezone.utc)
        attendu = attendu.astimezone().replace(tzinfo=None)
        self.assertEqual(utc, attendu)

    def test_un_decalage_explicite_est_respecte(self):
        avec = MA.instant("2026-09-13T16:00:00+02:00", self.JOUR)
        sans = MA.instant("2026-09-13T14:00:00Z", self.JOUR)
        self.assertEqual(avec, sans)

    def test_une_heure_seule_est_prise_pour_aujourd_hui(self):
        """Pratique pour ecrire un fichier d'essai a la main."""
        import datetime
        self.assertEqual(MA.instant("16:00", self.JOUR),
                         datetime.datetime(2026, 9, 13, 16, 0))

    def test_une_date_illisible_vaut_None(self):
        for mauvaise in ("", None, "demain", "25:00", {}):
            self.assertIsNone(MA.instant(mauvaise, self.JOUR), repr(mauvaise))

    # --- les accents ------------------------------------------------
    def test_les_accents_sont_translitteres(self):
        """L'ecran n'a que la police ASCII de MicroPython : un caractere
        accentue y sortirait en charabia. On convertit AVANT d'envoyer."""
        self.assertEqual(MA.sans_accents(u"Etude et modélisation 3D"),
                         "Etude et modelisation 3D")
        self.assertEqual(MA.sans_accents(u"Réunion à côté"),
                         "Reunion a cote")
        self.assertEqual(MA.sans_accents(u"l’Européenne"),
                         "l'Europeenne")

    def test_un_caractere_inconnu_devient_un_point_d_interrogation(self):
        """Un emoji dans un intitule de reunion, ca arrive. Il ne doit
        ni planter, ni dessiner n'importe quoi."""
        self.assertEqual(MA.sans_accents(u"Point \U0001F600 equipe"),
                         "Point ? equipe")

    # --- le filtrage ------------------------------------------------
    def test_seuls_les_evenements_du_jour_sont_gardes(self):
        evenements = self._du_jour({"evenements": [
            {"debut": "2026-09-12T10:00:00", "fin": "2026-09-12T11:00:00",
             "titre": "Hier"},
            {"debut": "2026-09-13T16:00:00", "fin": "2026-09-13T17:00:00",
             "titre": "Aujourd'hui"},
            {"debut": "2026-09-14T09:00:00", "fin": "2026-09-14T10:00:00",
             "titre": "Demain"},
        ]})
        self.assertEqual([e[2] for e in evenements], ["Aujourd'hui"])

    def test_les_evenements_sont_tries_et_convertis_en_minutes(self):
        evenements = self._du_jour({"evenements": [
            {"debut": "19:30", "fin": "21:00", "titre": "tache 1"},
            {"debut": "16:00", "fin": "17:00", "titre": "ELDV"},
        ]})
        self.assertEqual(evenements, [(16 * 60, 17 * 60, "ELDV"),
                                      (19 * 60 + 30, 21 * 60, "tache 1")])

    def test_une_reunion_qui_deborde_sur_demain_s_arrete_a_minuit(self):
        """Cette vue ne montre qu'aujourd'hui : une reunion de nuit ne
        doit pas produire une heure de fin situee hors de l'ecran."""
        evenements = self._du_jour({"evenements": [
            {"debut": "2026-09-13T23:00:00", "fin": "2026-09-14T01:00:00",
             "titre": "Astreinte"},
        ]})
        self.assertEqual(evenements[0][1], 23 * 60 + 59)

    def test_une_fin_absente_donne_une_duree_par_defaut(self):
        evenements = self._du_jour({"evenements": [
            {"debut": "16:00", "titre": "Sans fin"}]})
        self.assertEqual(evenements[0], (16 * 60, 16 * 60 + 30, "Sans fin"))

    def test_une_entree_sans_titre_est_ignoree(self):
        self.assertEqual(self._du_jour({"evenements": [
            {"debut": "16:00", "fin": "17:00", "titre": "   "},
            {"debut": "16:00", "fin": "17:00"},
            "pas un objet",
        ]}), [])

    def test_la_forme_brute_de_Microsoft_Graph_est_acceptee(self):
        """Pour qu'un export brut fonctionne SANS transformation : Graph
        imbrique ses dates et utilise des noms anglais."""
        evenements = self._du_jour({"value": [
            {"subject": u"Point d'équipe Atlas",
             "start": {"dateTime": "2026-09-13T11:00:00", "timeZone": "UTC"},
             "end": {"dateTime": "2026-09-13T12:00:00", "timeZone": "UTC"}},
        ]})
        self.assertEqual(evenements,
                         [(11 * 60, 12 * 60, "Point d'equipe Atlas")])

    def test_une_liste_nue_est_acceptee(self):
        self.assertEqual(
            self._du_jour([{"debut": "16:00", "fin": "17:00", "titre": "X"}]),
            [(16 * 60, 17 * 60, "X")])

    def test_la_liste_est_bornee(self):
        gros = [{"debut": "0%d:00" % (n % 10), "fin": "0%d:30" % (n % 10),
                 "titre": "R%d" % n} for n in range(40)]
        self.assertEqual(len(MA.evenements_du_jour(gros, self.JOUR,
                                                   maximum=16)), 16)

    # --- les lignes envoyees ----------------------------------------
    def test_les_lignes_du_protocole(self):
        lignes = MA.lignes_agenda([(16 * 60, 17 * 60, "ELDV"),
                                   (19 * 60 + 30, 21 * 60, "tache 1")])
        self.assertEqual(lignes, ["!AGBEGIN",
                                  "A:16:00|17:00|ELDV",
                                  "A:19:30|21:00|tache 1",
                                  "!AGEND"])

    def test_une_liste_vide_envoie_quand_meme_les_bornes(self):
        """Sinon la carte garderait l'agenda d'hier : une journee libre
        doit s'afficher comme libre."""
        self.assertEqual(MA.lignes_agenda([]), ["!AGBEGIN", "!AGEND"])

    def test_la_ligne_d_heure(self):
        import datetime
        self.assertEqual(
            MA.ligne_heure(datetime.datetime(2026, 9, 13, 19, 47)),
            "H:19:47|DIM 13")

    def test_les_lignes_produites_sont_relues_par_le_firmware(self):
        """Le controle qui compte : ce que le PC envoie, la carte le lit.

        Deux fichiers distincts, deux auteurs a des mois d'intervalle -
        c'est exactement la ou un format derive sans que personne ne le
        voie. On fait donc l'aller-retour complet.
        """
        sys.path.insert(0, str(RACINE / "device"))
        import time as _t
        _t.ticks_ms = getattr(_t, "ticks_ms", lambda: 0)
        _t.ticks_diff = getattr(_t, "ticks_diff", lambda a, b: a - b)
        import agenda as AG
        journee = AG.Agenda()
        evenements = self._du_jour({"evenements": [
            {"debut": "16:00", "fin": "17:30",
             "titre": u"ELDV - Etude et modélisation 3D"},
            {"debut": "19:30", "fin": "21:00", "titre": "tache 1"}]})
        import datetime
        self.assertTrue(journee.set_heure(
            MA.ligne_heure(datetime.datetime(2026, 9, 13, 19, 47))[2:], 0))
        for ligne in MA.lignes_agenda(evenements):
            if ligne == "!AGBEGIN":
                journee.commencer()
            elif ligne == "!AGEND":
                journee.terminer()
            else:
                self.assertTrue(journee.ajouter(ligne[2:]), ligne)
        self.assertEqual(journee.evenements, evenements)
        self.assertEqual(journee.jour, "DIM 13")
        self.assertEqual(journee.resume(19 * 60 + 47), (">21:00", "tache 1"))


class FichierAgenda(unittest.TestCase):
    """Le fichier peut manquer, etre illisible, ou etre en train d'etre
    reecrit par le flux qui le produit. Aucun de ces cas n'a le droit
    d'arreter le compagnon, ni d'effacer ce qui est deja affiche."""

    JOUR = __import__("datetime").date(2026, 9, 13)

    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.chemin = os.path.join(self.dossier, "agenda.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dossier, ignore_errors=True)

    def _ecrire(self, texte):
        with io.open(self.chemin, "w", encoding="utf-8") as fichier:
            fichier.write(texte)
        # Deux ecritures dans la meme milliseconde auraient la meme
        # signature : on force une date differente, comme le ferait le
        # temps reel entre deux mises a jour du flux.
        ancien = os.stat(self.chemin)
        os.utime(self.chemin, (ancien.st_atime, ancien.st_mtime + 10))

    def test_un_fichier_absent_ne_plante_pas(self):
        source = MA.SourceAgenda(self.chemin)
        self.assertFalse(source.relire(self.JOUR))
        self.assertEqual(source.evenements, [])

    def test_un_fichier_mal_forme_garde_la_liste_precedente(self):
        """Le flux est peut-etre en train d'ecrire : on reessaiera au
        tour suivant, sans effacer ce qui est affiche."""
        self._ecrire('{"evenements":[{"debut":"16:00","fin":"17:00",'
                     '"titre":"ELDV"}]}')
        source = MA.SourceAgenda(self.chemin)
        self.assertTrue(source.relire(self.JOUR))
        self._ecrire('{"evenements": [ceci n est pas du JSON')
        self.assertFalse(source.relire(self.JOUR))
        self.assertEqual([e[2] for e in source.evenements], ["ELDV"])

    def test_un_fichier_inchange_ne_declenche_rien(self):
        """Inutile de renvoyer le meme agenda deux fois par seconde."""
        self._ecrire('{"evenements":[{"debut":"16:00","fin":"17:00",'
                     '"titre":"ELDV"}]}')
        source = MA.SourceAgenda(self.chemin)
        self.assertTrue(source.relire(self.JOUR))
        self.assertFalse(source.relire(self.JOUR))

    def test_un_changement_est_detecte(self):
        self._ecrire('{"evenements":[{"debut":"16:00","fin":"17:00",'
                     '"titre":"ELDV"}]}')
        source = MA.SourceAgenda(self.chemin)
        source.relire(self.JOUR)
        self._ecrire('{"evenements":[{"debut":"19:30","fin":"21:00",'
                     '"titre":"tache 1"}]}')
        self.assertTrue(source.relire(self.JOUR))
        self.assertEqual([e[2] for e in source.evenements], ["tache 1"])

    def test_sans_chemin_la_source_ne_fait_rien(self):
        """Sans --agenda, le compagnon se comporte exactement comme avant."""
        source = MA.SourceAgenda(None)
        self.assertFalse(source.relire(self.JOUR))


class OuTrouverLAgenda(unittest.TestCase):
    """Personne ne lance ce script en tapant une ligne de commande.

    On double-clique sur macropad_auto.bat, et le raccourci de demarrage
    automatique ne passe que --journal. Une option --agenda oubliee, et la
    carte n'apprend jamais l'heure - en affichant "En attente du PC", un
    message qui fait chercher du cote de la liaison alors que tout va
    bien. D'ou un fichier par defaut, pose a cote du script.
    """

    def setUp(self):
        self.dossier = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_l_option_l_emporte_toujours(self):
        self.assertEqual(MA.chemin_agenda("C:/ailleurs.json", self.dossier),
                         "C:/ailleurs.json")

    def test_le_fichier_voisin_sert_par_defaut(self):
        voisin = os.path.join(self.dossier, MA.AGENDA_PAR_DEFAUT)
        with io.open(voisin, "w", encoding="utf-8") as fichier:
            fichier.write("{}")
        self.assertEqual(MA.chemin_agenda(None, self.dossier), voisin)

    def test_sans_rien_on_ne_devine_pas(self):
        """Pas de fichier = pas d'agenda. On n'invente pas un chemin."""
        self.assertIsNone(MA.chemin_agenda(None, self.dossier))

    def test_l_option_l_emporte_meme_si_un_voisin_existe(self):
        voisin = os.path.join(self.dossier, MA.AGENDA_PAR_DEFAUT)
        with io.open(voisin, "w", encoding="utf-8") as fichier:
            fichier.write("{}")
        self.assertEqual(MA.chemin_agenda("autre.json", self.dossier),
                         "autre.json")


class LeFuseauDeMicrosoftGraph(unittest.TestCase):
    """La forme que Graph produit VRAIMENT, et le piege qu'elle cache.

        {"dateTime": "2026-09-13T09:00:00.0000000", "timeZone": "UTC"}

    L'horodatage n'a NI Z NI DECALAGE : la seule mention du fuseau est le
    champ voisin. Le lire comme une heure locale decale tout l'agenda
    d'une ou deux heures selon la saison, sans que rien ne le signale.

    Ce defaut etait bien present dans la premiere version, et c'est
    tools/verifier_agenda.py qui l'a fait apparaitre - sur un fichier
    d'exemple, avant qu'il ne coute une reunion.
    """

    JOUR = __import__("datetime").date(2026, 9, 13)

    def _attendu(self, iso_utc):
        import datetime
        moment = datetime.datetime.fromisoformat(iso_utc).replace(
            tzinfo=datetime.timezone.utc)
        return moment.astimezone().replace(tzinfo=None)

    def test_le_champ_timeZone_a_cote_est_respecte(self):
        valeur = {"dateTime": "2026-09-13T09:00:00", "timeZone": "UTC"}
        self.assertEqual(MA.instant(valeur, self.JOUR),
                         self._attendu("2026-09-13T09:00:00"))

    def test_les_sept_decimales_de_Graph_passent(self):
        """Graph ecrit sept chiffres de seconde ; fromisoformat n'en
        accepte que trois ou six selon la version de Python. Sur un PC
        avec un Python plus ancien, tout l'agenda serait rejete."""
        valeur = {"dateTime": "2026-09-13T09:00:00.0000000",
                  "timeZone": "UTC"}
        self.assertEqual(MA.instant(valeur, self.JOUR),
                         self._attendu("2026-09-13T09:00:00"))

    def test_un_Z_dans_l_horodatage_marche_toujours(self):
        valeur = {"dateTime": "2026-09-13T09:00:00.0000000Z"}
        self.assertEqual(MA.instant(valeur, self.JOUR),
                         self._attendu("2026-09-13T09:00:00"))

    def test_un_fuseau_inconnu_n_est_PAS_devine(self):
        """Un fuseau invente serait exactement la panne silencieuse qu'on
        cherche a eviter. Faute de savoir, on prend l'heure telle quelle -
        et verifier_agenda.py le signale."""
        import datetime
        valeur = {"dateTime": "2026-09-13T09:00:00",
                  "timeZone": "Fuseau Qui N'existe Pas"}
        self.assertEqual(MA.instant(valeur, self.JOUR),
                         datetime.datetime(2026, 9, 13, 9, 0))

    def test_sans_timeZone_l_heure_reste_locale(self):
        import datetime
        valeur = {"dateTime": "2026-09-13T09:00:00"}
        self.assertEqual(MA.instant(valeur, self.JOUR),
                         datetime.datetime(2026, 9, 13, 9, 0))

    def test_un_dump_Graph_complet_donne_les_bonnes_heures(self):
        """Bout en bout, sur la forme brute d'un flux Power Automate."""
        evenements = MA.evenements_du_jour({"value": [
            {"subject": u"Point d'équipe Atlas",
             "start": {"dateTime": "2026-09-13T09:00:00.0000000",
                       "timeZone": "UTC"},
             "end": {"dateTime": "2026-09-13T10:00:00.0000000",
                     "timeZone": "UTC"}}]}, self.JOUR)
        attendu = self._attendu("2026-09-13T09:00:00")
        self.assertEqual(evenements,
                         [(attendu.hour * 60 + attendu.minute,
                           attendu.hour * 60 + attendu.minute + 60,
                           "Point d'equipe Atlas")])


class PourquoiUneEntreeEstEcartee(unittest.TestCase):
    """Une entree ecartee en silence donne "il manque des reunions" sans
    dire pourquoi. examiner_agenda() nomme chaque ecart."""

    JOUR = __import__("datetime").date(2026, 9, 13)

    def _raisons(self, entrees):
        _, rejets = MA.examiner_agenda({"evenements": entrees}, self.JOUR)
        return [raison for _, raison in rejets]

    def test_chaque_cause_est_nommee(self):
        raisons = self._raisons([
            {"debut": "2026-09-14T09:00:00", "fin": "2026-09-14T10:00:00",
             "titre": "Demain"},
            {"debut": "10:00", "fin": "11:00", "titre": "   "},
            {"titre": "Sans date"},
            "pas un objet",
        ])
        self.assertIn("pas aujourd'hui (2026-09-14)", raisons)
        self.assertTrue(any("titre" in r for r in raisons))
        self.assertTrue(any("debut" in r for r in raisons))
        self.assertTrue(any("objet" in r for r in raisons))

    def test_le_trop_plein_est_signale_aussi(self):
        gros = [{"debut": "0%d:00" % (n % 10), "fin": "0%d:30" % (n % 10),
                 "titre": "R%d" % n} for n in range(20)]
        gardes, rejets = MA.examiner_agenda({"evenements": gros}, self.JOUR,
                                            maximum=16)
        self.assertEqual(len(gardes), 16)
        self.assertEqual(len(rejets), 4)
        self.assertTrue(all("au-dela" in r for _, r in rejets))

    def test_un_agenda_parfait_n_a_aucun_rejet(self):
        gardes, rejets = MA.examiner_agenda(
            {"evenements": [{"debut": "10:00", "fin": "11:00",
                             "titre": "Propre"}]}, self.JOUR)
        self.assertEqual(len(gardes), 1)
        self.assertEqual(rejets, [])


class LesFormesPossiblesDUnFluxPowerAutomate(unittest.TestCase):
    """On ne peut pas verifier d'ici la forme exacte que produit le flux.

    Le connecteur Office 365 Outlook a plusieurs versions, et son vidage
    n'a pas la meme allure que celui de Microsoft Graph. Plutot que de
    parier sur une forme, on accepte celles qui sont plausibles : ca ne
    coute rien, et ca evite de dependre de ce qu'on ne peut pas voir.

    =================================================================
    POURQUOI CES TESTS FORCENT UN FUSEAU
    =================================================================
    Sur une machine reglee en UTC, "lire une heure comme locale" et "la
    lire comme UTC" sont LA MEME OPERATION. Un test ecrit sans precaution
    y passe donc meme si la conversion a ete supprimee - et c'est arrive :
    deux mutations ont survecu a la premiere version de cette classe.

    On impose donc un fuseau decale pendant ces tests. La ou c'est
    impossible - time.tzset() n'existe pas sous Windows - ils s'annoncent
    ignores plutot que de passer sans rien prouver.
    """

    JOUR = __import__("datetime").date(2026, 9, 13)
    FUSEAU = "Asia/Tokyo"          # UTC+9, sans heure d'ete : ecart stable

    @classmethod
    def setUpClass(cls):
        import time
        if not hasattr(time, "tzset"):
            raise unittest.SkipTest(
                "time.tzset() absent (Windows) : sans fuseau impose, ces "
                "tests ne prouveraient rien. Utilise tools/verifier_agenda.py")
        cls._tz_avant = os.environ.get("TZ")
        os.environ["TZ"] = cls.FUSEAU
        time.tzset()
        import datetime
        if datetime.datetime.now().astimezone().utcoffset() == \
                datetime.timedelta(0):
            raise unittest.SkipTest("le fuseau impose n'a pas pris")

    @classmethod
    def tearDownClass(cls):
        import time
        if cls._tz_avant is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = cls._tz_avant
        time.tzset()

    def _minutes(self, entree):
        gardes, rejets = MA.examiner_agenda({"evenements": [entree]},
                                            self.JOUR)
        self.assertEqual(rejets, [], "entree refusee : %s" % (rejets,))
        return gardes[0]

    def _utc_en_local(self, heure):
        """L'heure attendue a l'ecran pour une heure donnee en UTC."""
        import datetime
        moment = datetime.datetime(2026, 9, 13, heure, 0,
                                   tzinfo=datetime.timezone.utc).astimezone()
        return moment.hour * 60 + moment.minute

    def test_le_fuseau_est_bien_decale_pendant_ces_tests(self):
        """Le garde-fou du garde-fou : si cette assertion tombe, toutes
        les autres de cette classe ne prouvent plus rien."""
        self.assertNotEqual(self._utc_en_local(9), 9 * 60,
                            "fuseau non decale : les tests sont aveugles")

    def test_le_fuseau_annonce_au_niveau_de_l_entree(self):
        """Forme aplatie : start et end sont des chaines nues, et le
        fuseau est annonce UNE FOIS, a cote d'elles."""
        debut, fin, titre = self._minutes({
            "subject": "Atlas",
            "start": "2026-09-13T09:00:00.0000000",
            "end": "2026-09-13T10:00:00.0000000",
            "timeZone": "UTC"})
        self.assertEqual(debut, self._utc_en_local(9))
        self.assertEqual(fin, self._utc_en_local(10))
        self.assertEqual(titre, "Atlas")

    def test_un_champ_qui_porte_deja_son_fuseau_l_emporte(self):
        """startWithTimeZone porte son decalage : il n'y a plus rien a
        deviner, donc il passe AVANT le champ nu, qui lui est ambigu."""
        debut, _, _ = self._minutes({
            "subject": "Atlas",
            "start": "2026-09-13T09:00:00",
            "startWithTimeZone": "2026-09-13T09:00:00+00:00",
            "end": "2026-09-13T10:00:00",
            "endWithTimeZone": "2026-09-13T10:00:00+00:00"})
        self.assertEqual(debut, self._utc_en_local(9))

    def test_la_forme_imbriquee_de_Graph_marche_toujours(self):
        debut, _, _ = self._minutes({
            "subject": "Atlas",
            "start": {"dateTime": "2026-09-13T09:00:00.0000000",
                      "timeZone": "UTC"},
            "end": {"dateTime": "2026-09-13T10:00:00.0000000",
                    "timeZone": "UTC"}})
        self.assertEqual(debut, self._utc_en_local(9))

    def test_le_fichier_ecrit_a_la_main_reste_en_heure_locale(self):
        """Le cas le plus simple ne doit pas etre casse par les autres :
        sans aucune mention de fuseau, 09:00 veut dire 09:00 chez toi."""
        debut, fin, titre = self._minutes({
            "debut": "09:00", "fin": "10:00", "titre": "A la main"})
        self.assertEqual((debut, fin, titre), (540, 600, "A la main"))

    def test_summary_est_accepte_comme_titre(self):
        """Le nom qu'emploient les formats de calendrier ouverts."""
        _, _, titre = self._minutes({
            "summary": "Depuis un autre outil",
            "start": "09:00", "end": "10:00"})
        self.assertEqual(titre, "Depuis un autre outil")


class LeVraiVidageDUnFluxPowerAutomate(unittest.TestCase):
    """Un echantillon REEL, capture sur le flux d'un utilisateur.

    Jusqu'ici le format etait deduit, pas observe : je n'ai ni Windows, ni
    Teams, ni Power Automate. Ce vidage est la vraie sortie du connecteur
    Office 365 Outlook, action "Obtenir une vue Calendrier des evenements
    (V3)", reduite aux champs qui nous concernent.

    Il confirme la forme APLATIE, et il justifie deux choix faits a
    l'aveugle :

      - "start" est nu (aucun Z, aucun decalage) mais un champ voisin
        "startWithTimeZone" porte le decalage, et "timeZone" est declare
        au niveau de l'entree. Lire "start" seul decalerait tout ;
      - le connecteur ecrit SEPT decimales de seconde.
    """

    JOUR = __import__("datetime").date(2026, 9, 13)

    VIDAGE = {"value": [
        {"subject": "ha",
         "start": "2026-09-13T20:30:00.0000000",
         "end": "2026-09-13T21:30:00.0000000",
         "startWithTimeZone": "2026-09-13T20:30:00+00:00",
         "endWithTimeZone": "2026-09-13T21:30:00+00:00",
         "body": "", "isHtml": True, "timeZone": "UTC",
         "isAllDay": False, "recurrence": "none", "showAs": "busy"},
        {"subject": "a",
         "start": "2026-09-14T07:00:00.0000000",
         "end": "2026-09-14T08:00:00.0000000",
         "startWithTimeZone": "2026-09-14T07:00:00+00:00",
         "endWithTimeZone": "2026-09-14T08:00:00+00:00",
         "body": "", "isHtml": True, "timeZone": "UTC",
         "isAllDay": False, "recurrence": "none", "showAs": "busy"},
    ]}

    def _utc_en_local(self, jour, heure, minute=0):
        import datetime
        moment = datetime.datetime(2026, 9, jour, heure, minute,
                                   tzinfo=datetime.timezone.utc).astimezone()
        return moment

    def test_le_vidage_reel_est_lu_correctement(self):
        gardes, rejets = MA.examiner_agenda(self.VIDAGE, self.JOUR)

        # L'evenement du jour, converti depuis UTC vers l'heure du PC.
        debut = self._utc_en_local(13, 20, 30)
        fin = self._utc_en_local(13, 21, 30)
        if debut.date() != self.JOUR:
            self.skipTest("fuseau du PC trop decale pour ce cas")
        self.assertEqual(gardes, [(debut.hour * 60 + debut.minute,
                                   fin.hour * 60 + fin.minute, "ha")])

        # Celui de demain est ECARTE, avec sa raison nommee.
        self.assertEqual(len(rejets), 1)
        self.assertIn("pas aujourd'hui", rejets[0][1])

    def test_le_champ_nu_n_est_pas_celui_qui_est_lu(self):
        """Le controle qui compte : 'start' et 'startWithTimeZone' portent
        ici la MEME heure, donc ce test ne prouverait rien tel quel. On
        desaccorde volontairement les deux pour voir lequel est lu."""
        import copy
        vidage = copy.deepcopy(self.VIDAGE)
        vidage["value"][0]["start"] = "2026-09-13T03:00:00.0000000"
        gardes, _ = MA.examiner_agenda(vidage, self.JOUR)
        attendu = self._utc_en_local(13, 20, 30)
        if attendu.date() != self.JOUR:
            self.skipTest("fuseau du PC trop decale pour ce cas")
        self.assertEqual(gardes[0][0], attendu.hour * 60 + attendu.minute,
                         "c'est le champ NU qui a ete lu, pas celui qui "
                         "porte son fuseau")

    def test_les_champs_inutiles_ne_genent_pas(self):
        """Le vidage porte une trentaine de champs dont on ne fait rien -
        webLink, iCalUId, organizer... Aucun ne doit perturber la lecture."""
        gardes, _ = MA.examiner_agenda(self.VIDAGE, self.JOUR)
        self.assertEqual([titre for _, _, titre in gardes], ["ha"])


class TrouverLAgendaDansOneDrive(unittest.TestCase):
    """La derniere piece pour que la chaine tourne sans rien taper.

    Power Automate depose le fichier dans OneDrive ; Windows pose le
    chemin de ce dossier dans une variable d'environnement. Sans cette
    recherche, il fallait passer --agenda a la main - donc ouvrir une
    console, donc y penser, donc ne pas le faire.
    """

    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.onedrive = tempfile.mkdtemp()
        self._avant = {v: os.environ.get(v) for v in MA._VARIABLES_ONEDRIVE}
        for variable in MA._VARIABLES_ONEDRIVE:
            os.environ.pop(variable, None)

    def tearDown(self):
        import shutil
        for variable, valeur in self._avant.items():
            if valeur is None:
                os.environ.pop(variable, None)
            else:
                os.environ[variable] = valeur
        shutil.rmtree(self.dossier, ignore_errors=True)
        shutil.rmtree(self.onedrive, ignore_errors=True)

    def _poser(self, dossier):
        chemin = os.path.join(dossier, MA.AGENDA_PAR_DEFAUT)
        with io.open(chemin, "w", encoding="utf-8") as fichier:
            fichier.write("{}")
        return chemin

    def test_le_onedrive_professionnel_est_fouille(self):
        os.environ["OneDriveCommercial"] = self.onedrive
        attendu = self._poser(self.onedrive)
        self.assertEqual(MA.chemin_agenda(None, self.dossier), attendu)

    def test_le_onedrive_personnel_aussi(self):
        os.environ["OneDrive"] = self.onedrive
        attendu = self._poser(self.onedrive)
        self.assertEqual(MA.chemin_agenda(None, self.dossier), attendu)

    def test_le_dossier_du_script_passe_avant_OneDrive(self):
        """Un fichier pose a cote du script est un choix explicite : il
        doit l'emporter sur celui que le flux depose."""
        os.environ["OneDriveCommercial"] = self.onedrive
        self._poser(self.onedrive)
        attendu = self._poser(self.dossier)
        self.assertEqual(MA.chemin_agenda(None, self.dossier), attendu)

    def test_l_option_l_emporte_sur_tout(self):
        os.environ["OneDriveCommercial"] = self.onedrive
        self._poser(self.onedrive)
        self._poser(self.dossier)
        self.assertEqual(MA.chemin_agenda("impose.json", self.dossier),
                         "impose.json")

    def test_un_OneDrive_sans_agenda_ne_donne_rien(self):
        """On ne rend jamais un chemin qui n'existe pas : le message
        d'erreur qui suivrait serait un faux coupable."""
        os.environ["OneDriveCommercial"] = self.onedrive
        self.assertIsNone(MA.chemin_agenda(None, self.dossier))

    def test_les_lieux_fouilles_sont_annonces(self):
        """Sans cette liste, "aucun agenda trouve" n'aide personne."""
        os.environ["OneDriveCommercial"] = self.onedrive
        lieux = MA.dossiers_agenda(self.dossier)
        self.assertEqual(lieux[0], self.dossier)
        self.assertIn(self.onedrive, lieux)
