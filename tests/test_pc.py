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
