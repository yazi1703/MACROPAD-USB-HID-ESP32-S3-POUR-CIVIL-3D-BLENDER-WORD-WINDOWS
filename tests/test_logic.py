"""Tests sur PC : temps, GPIO et transport simulés ; aucune validation USB physique."""
import ast, json, os, shutil, subprocess, sys, tempfile, types, pathlib, unittest, time, runpy
from unittest.mock import patch
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'device'), str(ROOT/'device/lib')]
PERIOD = 1 << 30
clock = [0]
time.ticks_ms = lambda: clock[0]
time.ticks_add = lambda a, b: (a+b) % PERIOD
time.ticks_diff = lambda a, b: ((a-b+PERIOD//2) % PERIOD)-PERIOD//2
time.sleep_ms = lambda ms: clock.__setitem__(0, (clock[0]+ms) % PERIOD)
sys.modules['utime'] = time
machine = types.ModuleType('machine')
class Pin:
    IN, OUT, PULL_UP, PULL_DOWN = range(4)
    levels = {}
    def __init__(self, n, mode=None, pull=None, value=None):
        self.n = n
        if value is not None: self.levels[n] = value
        elif n not in self.levels: self.levels[n] = 0 if pull == self.PULL_DOWN else 1
    def value(self): return self.levels[self.n]
class PWM:
    def __init__(self, *a, **kw): self.values=[]
    def duty_u16(self, v): self.values.append(v)
    def deinit(self): pass
machine.Pin, machine.PWM = Pin, PWM
machine.USBDevice = type('USBDevice', (), {})
sys.modules['machine'] = machine
mp = types.ModuleType('micropython'); mp.const=lambda v:v; sys.modules['micropython']=mp
from inputs import Debouncer
from profiles import ProfileManager, PROFILES, TESTS
from layouts import compile_actions, character_keys, letter_code
from hid_keyboard import HIDKeyboard
from led import Led, breath
import config as C
class Transport:
    def __init__(self): self.sent=[]; self.open=True; self.blocked=False; self.led_mask=0; self.error=False
    def is_open(self): return self.open
    def busy(self): return self.blocked
    def send_keys(self, keys, timeout_ms=100):
        assert timeout_ms == 0
        if self.error: raise OSError('simulated failure')
        self.sent.append(tuple(keys)); return True

def pump(k, start, duration):
    for n in range(start,start+duration,2):
        clock[0]=n % PERIOD; k.tick(clock[0])

class Logic(unittest.TestCase):
    def setUp(self): clock[0]=0; Pin.levels={}
    def test_profiles_all_directions(self):
        p=ProfileManager(C.PROFILES_ORDER,C.DEFAULT_PROFILE)
        self.assertEqual([p.move(1) for _ in range(4)],['WORD','WINDOWS','BLENDER','CIVIL3D'])
        self.assertEqual([p.move(-1) for _ in range(4)],['BLENDER','WINDOWS','WORD','CIVIL3D'])
    def test_bounce_hold_release(self):
        d=Debouncer(False,25,0)
        events=[d.update(v,t) for t,v in [(0,1),(4,0),(8,1),(32,1),(33,1),(1000,1),(1001,0),(1026,0),(1100,1),(1125,1)]]
        self.assertEqual(events,[0,0,0,0,1,0,0,-1,0,1])
    def test_start_held(self):
        d=Debouncer(True,25,0)
        self.assertEqual(d.update(True,200),0)
        d.update(False,201); self.assertEqual(d.update(False,226),-1)
        d.update(True,250); self.assertEqual(d.update(True,275),1)
    def test_ticks_wrap(self):
        d=Debouncer(False,25,PERIOD-20)
        d.update(True,PERIOD-10)
        self.assertEqual(d.update(True,14),0)
        self.assertEqual(d.update(True,15),1)
    def test_azerty_all_letters(self):
        expected=[20,5,6,7,8,9,10,11,12,13,14,15,51,17,18,19,4,21,22,23,24,25,29,27,28,26]
        for char,code in zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',expected):
            self.assertEqual(character_keys(char,'FR_AZERTY'),(-2,code))
            self.assertEqual(character_keys(char.lower(),'FR_AZERTY'),(code,))
        self.assertEqual(character_keys('_','FR_AZERTY'),(37,))
        self.assertEqual(character_keys('_','US_QWERTY'),(-2,45))
    def test_capslock_mapping(self):
        self.assertEqual(character_keys('A','FR_AZERTY',True),(20,))
        self.assertEqual(character_keys('a','FR_AZERTY',True),(-2,20))
    def test_macros_valid_and_enter(self):
        for macros in PROFILES.values():
            for _, gestes in macros:
                for actions in gestes.values():
                    self.assertTrue(compile_actions(actions,'FR_AZERTY'))
        # B3 et B4 de CIVIL3D ecrivent une commande _XXX suivie d'Entree.
        # B1 est le presse-papiers, B2 la touche modificatrice.
        for index in (2,3):
            seq=compile_actions(PROFILES['CIVIL3D'][index][1]['court'],'FR_AZERTY')
            self.assertEqual(seq[0],(37,)); self.assertEqual(seq[-1],(40,))
        self.assertEqual(compile_actions([('combo',('CTRL','Z'))],'FR_AZERTY'),[(-1,26)])
        # La touche 1 est le presse-papiers dans TOUS les profils.
        for nom, macros in PROFILES.items():
            label, gestes = macros[0]
            self.assertEqual(label, 'COPIER', nom)
            self.assertEqual(gestes['court'], [('combo',('CTRL','C'))], nom)
            self.assertEqual(gestes['double'], [('combo',('CTRL','V'))], nom)
            self.assertEqual(gestes['long'], [('combo',('CTRL','Z'))], nom)
    def test_invalid_text_atomic(self):
        t=Transport(); k=HIDKeyboard(t); k.tick(0)
        with self.assertRaises(ValueError): k.submit([('text','ABC€')])
        self.assertEqual(k.queue,[]); self.assertEqual(t.sent,[()])
    def test_press_release_every_combo(self):
        t=Transport(); k=HIDKeyboard(t); k.tick(0)
        k.submit([('combo',('CTRL','SHIFT','ESC'))]); pump(k,2,100)
        self.assertEqual(t.sent,[(),(-1,-2,41),()]); self.assertTrue(k.idle())
    def test_escape_preempts_modifier_and_text(self):
        t=Transport(); k=HIDKeyboard(t); k.tick(0)
        k.submit([('combo',('ALT','TAB')),('text','ABC')]); k.tick(2)
        self.assertEqual(t.sent[-1],(-4,43))
        k.escape(3); pump(k,4,100)
        self.assertEqual(t.sent,[(),(-4,43),(),(41,),()])
    def test_busy_does_not_lose_event(self):
        t=Transport(); k=HIDKeyboard(t); k.tick(0); k.submit([('text','a')])
        t.blocked=True; pump(k,2,100); self.assertEqual(t.sent,[()])
        t.blocked=False; pump(k,102,100); self.assertEqual(t.sent,[(),(20,),()])
    def test_disconnect_discards_queue(self):
        t=Transport(); k=HIDKeyboard(t); k.tick(0); k.submit([('text','ABC')]); k.tick(2)
        t.open=False; k.tick(4); t.open=True; pump(k,6,100)
        self.assertEqual(t.sent[-1],()); self.assertTrue(k.idle())
        self.assertNotIn((-2,5), t.sent)
    def test_fault_releases_without_resume(self):
        t=Transport(); k=HIDKeyboard(t); k.tick(0)
        k.submit([('combo',('WIN','E'))]); k.tick(2)
        t.error=True; k.tick(20); self.assertTrue(k.fault)
        t.error=False; k.tick(22); self.assertEqual(t.sent[-1],())
        self.assertFalse(k.submit([('text','a')]))
    def test_timeout_cancels_pending(self):
        t=Transport(); k=HIDKeyboard(t); k.tick(0); k.submit([('text','a')]); t.blocked=True
        pump(k,2,1100); self.assertTrue(k.fault)
        t.blocked=False; k.tick(1104); self.assertEqual(t.sent,[(),()])
    def test_queue_limit(self):
        t=Transport(); k=HIDKeyboard(t); k.tick(0)
        for _ in range(C.MACRO_QUEUE_LIMIT): self.assertTrue(k.submit([('text','a')]))
        self.assertFalse(k.submit([('text','a')]))
    def test_breath_and_flash(self):
        values=[breath(t) for t in range(C.LED_PERIOD_MS)]
        self.assertAlmostEqual(min(values),C.LED_MIN)
        self.assertAlmostEqual(max(values),C.LED_MAX)
        self.assertAlmostEqual(breath(0),breath(C.LED_PERIOD_MS))
        self.assertLess(max(abs(a-b) for a,b in zip(values,values[1:])),0.001)
        l=Led(); l.flash(0); l.tick(100); self.assertEqual(l.pwm.values[-1],65535)
        l.tick(470); self.assertLessEqual(l.pwm.values[-1],int(C.LED_MAX*65535)); l.close()
        self.assertEqual(l.pwm.values[-1],0)
    def test_led_wrap(self):
        clock[0]=PERIOD-10; l=Led(); l.tick(10); self.assertEqual(l.phase,20)
    def test_safe_mode_never_initializes_hid(self):
        import runtime
        with patch.object(C,'HID_ENABLED',True), patch('hid_keyboard.create_interface') as create:
            Pin.levels[4]=0; runpy.run_path(str(ROOT/'device/boot.py'))
            self.assertTrue(runtime.safe_mode); create.assert_not_called()
        runtime.safe_mode=False
    def test_oled_absent_nonfatal(self):
        from display import Display
        d=Display(); self.assertIsNone(d.oled)
        d.profile('WORD', [('BOLD', [('combo', ('CTRL','B'))])], 0, 0, 4)
        d.tick(0); d.set_etat('HID'); d.config_screen('X','Y','1.2.3.4')
    def test_vendor_report_bytes(self):
        from usb.device.keyboard import KeyboardInterface
        class Capture(KeyboardInterface):
            def __init__(self): self.reports=[]; super().__init__()
            def send_report(self, report, timeout_ms=100): self.reports.append(bytes(report)); return True
        keyboard=Capture(); keyboard.send_keys((-1,-2,41)); keyboard.send_keys(())
        self.assertEqual(keyboard.reports,[bytes([3,0,41,0,0,0,0,0]),bytes(8)])

    def test_safe_mode_main_returns_to_repl(self):
        import main, runtime
        with patch.object(runtime, 'safe_mode', True), patch.object(main, 'Inputs') as inputs:
            main.run(); inputs.assert_not_called()
    def test_oled_transfer_failure_disables_only_display(self):
        from display import Display
        d=Display()
        class Broken:
            def write_cmd(self, c): raise OSError('I2C cable removed')
        d.oled=Broken(); d.pending_page=0
        d.tick(0); self.assertIsNone(d.oled)
    def test_oled_transmits_one_page_per_tick(self):
        from display import Display
        d=Display()
        class Screen:
            displaybuf=bytearray(1024)
            def __init__(self): self.data=[]
            def write_cmd(self, c): pass
            def write_data(self, b): self.data.append(bytes(b))
        screen=Screen(); d.oled=screen; d.pending_page=0
        d.tick(0); self.assertEqual(len(screen.data),1); self.assertEqual(len(screen.data[0]),128)
        for t in range(1,15): d.tick(t)
        self.assertEqual(len(screen.data),8)
    def test_main_cooperative_integration(self):
        import main, runtime
        t=Transport()
        def simulated_sleep(ms):
            clock[0]+=ms
            # Chronologie physique : appui macro, changement profil, ESC.
            # On se sert de B3 (GPIO6, _MATCHPROP) : B1 est le presse-papiers
            # et son double appui retarde volontairement l'appui court, B2
            # est la touche modificatrice.
            Pin.levels[6]=0 if 2600 <= clock[0] < 2660 else 1
            Pin.levels[11]=1 if 2700 <= clock[0] < 2780 else 0
            Pin.levels[14]=0 if 2900 <= clock[0] < 2960 else 1
            if clock[0] >= 3200: raise KeyboardInterrupt()
        with patch.object(runtime, 'interface', t), patch.object(runtime, 'safe_mode', False), patch.object(main, 'sleep_ms', simulated_sleep):
            with self.assertRaises(KeyboardInterrupt): main.run()
        self.assertIn((37,),t.sent)  # Début de commande Civil3D.
        self.assertIn((41,),t.sent)  # ESC après le passage WORD.
        self.assertEqual(t.sent[-1],())
        self.assertEqual(Pin.levels[15],0)


class Corrections(unittest.TestCase):
    """Tests des corrections apportées au projet initial.

    Chaque test ci-dessous correspond à un défaut réel trouvé dans la V0 ;
    il échouerait sur la version d'origine.
    """

    def setUp(self):
        clock[0] = 0
        Pin.levels = {}

    # --- Correction 1 : Verr. Maj cassait le "_" des commandes Civil 3D ----
    def test_capslock_underscore_fr(self):
        # Verr. Maj éteint : le "_" est la touche 37 sans Maj.
        self.assertEqual(character_keys('_', 'FR_AZERTY', False), (37,))
        # Verr. Maj allumé : sous Windows FR la rangée des chiffres est
        # inversée, il faut donc Maj pour obtenir "_".
        # Sans cette correction, Civil 3D recevait "8MATCHPROP".
        self.assertEqual(character_keys('_', 'FR_AZERTY', True), (-2, 37))

    def test_capslock_digits_fr(self):
        self.assertEqual(character_keys('1', 'FR_AZERTY', False), (-2, 30))
        self.assertEqual(character_keys('1', 'FR_AZERTY', True), (30,))

    def test_capslock_us_only_affects_letters(self):
        # En QWERTY, Verr. Maj n'agit QUE sur les lettres.
        self.assertEqual(character_keys('_', 'US_QWERTY', True), (-2, 45))
        self.assertEqual(character_keys('1', 'US_QWERTY', True), (30,))
        self.assertEqual(character_keys('a', 'US_QWERTY', True), (-2, 4))

    def test_commands_typable_with_capslock_on(self):
        # Les trois commandes doivent rester correctes Verr. Maj allumé.
        for command in ('_MATCHPROP', '_HATCH', '_ISOLATEOBJECTS'):
            frappes = compile_actions([('text_enter', command)],
                                      'FR_AZERTY', True)
            self.assertEqual(len(frappes), len(command) + 1)
            self.assertEqual(frappes[0], (-2, 37))   # le "_" corrigé

    # --- Correction 2 : table de caractères complète ----------------------
    def test_extended_characters(self):
        from layouts import TABLES
        self.assertGreater(len(TABLES['FR_AZERTY']), 100)
        for char in '.,;:/*-+=()!?%@#':
            character_keys(char, 'FR_AZERTY')      # ne doit pas lever
            character_keys(char, 'US_QWERTY')

    def test_combo_accepts_digits_and_symbols(self):
        from layouts import key_code
        # Ctrl+1 était refusé et empêchait main.py de démarrer.
        self.assertEqual(key_code('1', 'FR_AZERTY'), 30)
        compile_actions([('combo', ('CTRL', '1'))], 'FR_AZERTY')

    def test_shortcut_uses_physical_key_not_character(self):
        from layouts import key_code
        # Ctrl+Z sur AZERTY doit viser la touche qui écrit "z" (26),
        # surtout pas le "Z" américain (29) qui vaudrait Ctrl+W = fermer.
        self.assertEqual(key_code('Z', 'FR_AZERTY'), 26)
        self.assertEqual(key_code('Z', 'US_QWERTY'), 29)

    # --- Correction 3 : macro perdue juste après un changement de profil --
    def test_submit_accepted_right_after_cancel(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.cancel()                       # ce que fait un changement de profil
        self.assertTrue(k.submit([('text', 'a')]))
        pump(k, 2, 200)
        self.assertIn((20,), t.sent)     # "a" en AZERTY = touche 20 (le Q du QWERTY)

    def test_submit_accepted_right_after_escape(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.escape(0)
        self.assertTrue(k.submit([('combo', ('CTRL', 'Z'))]))

    # --- Correction 4 : close() ne débranchait plus l'USB sans raison -----
    def test_close_keeps_usb_when_nothing_pressed(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        self.assertFalse(k.keys_down)
        k.close()          # ne doit toucher ni à usb.device ni au REPL
        self.assertFalse(k.fault)

    def test_close_after_macro_leaves_nothing_pressed(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.submit([('combo', ('CTRL', 'SHIFT', 'ESC'))])
        pump(k, 2, 200)
        self.assertEqual(t.sent[-1], ())     # dernier paquet = tout relâché
        self.assertFalse(k.keys_down)
        k.close()

    # --- Correction 5 : ESC réellement instantané -------------------------
    def test_esc_fast_edge_is_immediate(self):
        d = Debouncer(False, 20, 0, fast=True)
        self.assertEqual(d.update(True, 0), 1)     # aucun retard
        self.assertEqual(d.update(False, 5), 0)    # rebond ignoré
        self.assertEqual(d.update(True, 10), 0)
        self.assertEqual(d.update(True, 25), 0)    # maintien : pas de répétition
        self.assertEqual(d.update(False, 40), -1)
        self.assertEqual(d.update(True, 70), 1)    # nouvel appui accepté

    def test_esc_fast_edge_held_at_boot(self):
        d = Debouncer(True, 20, 0, fast=True)      # touche tenue au démarrage
        self.assertEqual(d.update(True, 0), 0)     # aucun appui parasite
        self.assertEqual(d.update(False, 30), -1)
        self.assertEqual(d.update(True, 60), 1)

    # --- Correction 6 : ordre de lecture garanti --------------------------
    def test_input_order_is_deterministic(self):
        from inputs import Inputs
        controls = Inputs()
        noms = [name for name, _ in controls.sequence]
        self.assertEqual(noms[0], 'ESC')           # ESC toujours lu en premier
        attendu = ['ESC'] + ['B%d' % (i + 1) for i in range(len(C.BUTTON_PINS))]
        attendu += ['PREVIOUS', 'NEXT']
        self.assertEqual(noms, attendu)



class BugChangementDeProfil(unittest.TestCase):
    """Panne constatee sur le materiel : un changement de profil apres un
    moment de repos declenchait « transfert sans progression » et bloquait
    definitivement le clavier."""

    def setUp(self):
        clock[0] = 0
        Pin.levels = {}

    def test_cancel_apres_repos_ne_declenche_pas_de_panne(self):
        t = Transport()
        k = HIDKeyboard(t)
        k.tick(0)                       # ouverture + relachement initial
        # Le macropad reste au repos bien plus longtemps que HID_TIMEOUT_MS.
        for n in range(0, 30000, 500):
            clock[0] = n
            k.tick(n)
        self.assertFalse(k.fault)
        # L'utilisateur touche un TTP223 : main.py appelle cancel().
        clock[0] = 30000
        k.cancel()
        k.tick(30000)
        self.assertFalse(k.fault)       # echouait avant la correction
        self.assertTrue(k.submit([('text', 'a')]))
        pump(k, 30002, 300)
        self.assertIn((20,), t.sent)    # la macro suivante part bien

    def test_le_vrai_blocage_declenche_toujours_la_panne(self):
        # On verifie que la correction n'a pas desarme le garde-fou.
        t = Transport()
        k = HIDKeyboard(t)
        k.tick(0)
        k.submit([('text', 'abc')])
        t.blocked = True                # l'endpoint ne se libere jamais
        pump(k, 2, 3000)
        self.assertTrue(k.fault)

    def test_reconnexion_usb_efface_la_panne(self):
        t = Transport()
        k = HIDKeyboard(t)
        k.tick(0)
        k._fail('panne simulee')
        self.assertTrue(k.fault)
        t.open = False
        k.tick(10)                      # cable debranche
        t.open = True
        k.tick(20)                      # rebranche : l'hote reconfigure tout
        self.assertFalse(k.fault)
        self.assertTrue(k.submit([('text', 'a')]))



class V1SixTouchesEtConfigWeb(unittest.TestCase):
    """Tests des nouveautes V1 : six touches, profils en JSON, page web."""

    def setUp(self):
        clock[0] = 0
        Pin.levels = {}
        self.fichier = C.PROFILES_FILE
        try:
            import os
            os.remove(self.fichier)
        except OSError:
            pass

    tearDown = setUp

    # --- six touches ---------------------------------------------------
    def test_six_touches_partout(self):
        import profiles as P
        self.assertEqual(len(C.BUTTON_PINS), 6)
        for nom in C.PROFILES_ORDER:
            self.assertEqual(len(P.PROFILES[nom]), 6, nom)

    def test_libelles_tiennent_sur_l_ecran(self):
        import profiles as P
        for nom, macros in P.PROFILES.items():
            for label, _gestes in macros:
                self.assertLessEqual(len(label), P.LABEL_MAX,
                                     "%s : '%s'" % (nom, label))

    def test_toutes_les_macros_usine_sont_tapables(self):
        import profiles as P
        for nom, macros in P.PROFILES.items():
            for label, gestes in macros:
                for actions in gestes.values():
                    compile_actions(actions, C.KEYBOARD_LAYOUT)

    def test_rotation_sur_six_touches(self):
        from profiles import ProfileManager
        import store
        profils, ordre, titres, couleurs, apps, repli, origine = store.charger(6)
        self.assertEqual(origine, 'usine')
        p = ProfileManager(ordre, C.DEFAULT_PROFILE, profils, 6)
        self.assertEqual(len(p.macros), 6)
        self.assertEqual([p.move(1) for _ in range(4)],
                         ['WORD', 'WINDOWS', 'BLENDER', 'CIVIL3D'])

    # --- enregistrement JSON --------------------------------------------
    def test_aller_retour_json(self):
        import store
        profils, ordre, titres, couleurs, apps, repli = store.defauts()
        ok, raison = store.enregistrer(profils, ordre, titres, couleurs, apps, repli, 6)
        self.assertTrue(ok, raison)
        relus, ordre2, titres2, couleurs2, apps2, repli2, origine = store.charger(6)
        self.assertEqual(origine, 'fichier')
        self.assertEqual(ordre2, ordre)
        self.assertEqual(apps2, apps)          # la table des logiciels survit
        self.assertEqual(repli2, repli)
        # Les macros relues doivent produire exactement les memes frappes,
        # geste par geste.
        for nom in ordre:
            for i in range(6):
                for geste in ('court', 'long', 'double'):
                    self.assertEqual(
                        compile_actions(relus[nom][i][1].get(geste, []), 'FR_AZERTY'),
                        compile_actions(profils[nom][i][1].get(geste, []), 'FR_AZERTY'),
                        '%s B%d %s' % (nom, i + 1, geste))

    def test_macro_intapable_refusee(self):
        import store
        profils, ordre, titres, couleurs, apps, repli = store.defauts()
        profils['CIVIL3D'][0] = ('KO', {'court': [('key', 'TOUCHE_BIDON')]})
        ok, raison = store.enregistrer(profils, ordre, titres, couleurs, apps, repli, 6)
        self.assertFalse(ok)
        self.assertIn('CIVIL3D', raison)

    def test_libelle_trop_long_refuse(self):
        import store
        profils, ordre, titres, couleurs, apps, repli = store.defauts()
        profils['WORD'][0] = ('BEAUCOUPTROPLONG', {'court': [('key', 'A')]})
        ok, raison = store.enregistrer(profils, ordre, titres, couleurs, apps, repli, 6)
        self.assertFalse(ok)

    def test_fichier_corrompu_repli_sur_usine(self):
        import store
        with open(C.PROFILES_FILE, 'w') as f:
            f.write('{ ceci n est pas du JSON')
        profils, ordre, titres, couleurs, apps, repli, origine = store.charger(6)
        self.assertEqual(origine, 'usine')      # ne doit PAS planter
        self.assertEqual(len(profils['CIVIL3D']), 6)

    def test_fichier_incoherent_repli_sur_usine(self):
        import store, json as J
        # JSON valide, mais une macro impossible a taper.
        touche = {'label': 'A', 'court': {'type': 'key', 'valeur': 'INCONNU'}}
        data = {'version': 2, 'ordre': ['X'],
                'profils': {'X': {'titre': 'X', 'touches': [touche] * 6}}}
        with open(C.PROFILES_FILE, 'w') as f:
            J.dump(data, f)
        profils, ordre, titres, couleurs, apps, repli, origine = store.charger(6)
        self.assertEqual(origine, 'usine')

    def test_conversion_combo(self):
        import store
        self.assertEqual(store.action_vers_json([('combo', ('CTRL', 'SHIFT', 'ESC'))]),
                         ('combo', 'CTRL+SHIFT+ESC'))
        self.assertEqual(store.action_depuis_json('combo', 'CTRL+SHIFT+ESC'),
                         [('combo', ('CTRL', 'SHIFT', 'ESC'))])
        self.assertEqual(store.action_depuis_json('none', ''), [])

    # --- affichage six touches ------------------------------------------
    def test_affichage_six_touches_sans_debordement(self):
        # Faux ecran : il ne dessine rien, il compte les ecritures qui
        # sortiraient des 128x64 pixels reels de la dalle.
        class EcranFactice:
            def __init__(self):
                self.displaybuf = bytearray(1024)
                self.out_of_bounds = 0
                self.pages = []

            def _v(self, x, y, w=1, h=1):
                if x < 0 or y < 0 or x + w > 128 or y + h > 64:
                    self.out_of_bounds += 1

            def fill(self, c):
                pass

            def fill_rect(self, x, y, w, h, c):
                self._v(x, y, w, h)

            def rect(self, x, y, w, h, c):
                self._v(x, y, w, h)

            def hline(self, x, y, w, c):
                self._v(x, y, w, 1)

            def vline(self, x, y, h, c):
                self._v(x, y, 1, h)

            def text(self, s, x, y, c=1):
                if y >= 54:
                    # Ligne du bas : le defilement du nom de fichier ecrit
                    # VOLONTAIREMENT en dehors de l'ecran, framebuf coupe
                    # ce qui depasse. On ne verifie donc que la hauteur.
                    if y < 0 or y + 8 > 64:
                        self.out_of_bounds += 1
                    return
                self._v(x, y, 8 * len(s), 8)

            def write_cmd(self, c):
                pass

            def write_data(self, b):
                self.pages.append(bytes(b))

        # Faux framebuf, utilise par l'agrandissement de police du splash.
        fb = types.ModuleType('framebuf')

        class _FB:
            def __init__(self, buf, w, h, fmt):
                self.w, self.h, self.px = w, h, set()

            def fill(self, c):
                self.px.clear()

            def text(self, s, x, y, c=1):
                for i, ch in enumerate(s):
                    for r in range(8):
                        for col in range(7):
                            if (r + col + ord(ch)) % 3 == 0:
                                self.px.add((x + i * 8 + col, y + r))

            def pixel(self, x, y):
                return 1 if (x, y) in self.px else 0

        fb.FrameBuffer = _FB
        fb.MONO_HLSB = 3
        fb.MONO_VLSB = 0
        sys.modules['framebuf'] = fb

        from display import Display
        import profiles as P
        ecran = Display()
        ecran.oled = EcranFactice()

        for index, nom in enumerate(C.PROFILES_ORDER):
            ecran.profile(P.TITLES.get(nom, nom), P.PROFILES[nom], clock[0],
                          index, len(C.PROFILES_ORDER), True)
            for _ in range(C.PROFILE_SPLASH_MS + 100):
                ecran.tick(clock[0])
                clock[0] += 1
            ecran.set_etat('HID')

            # Le saut sur la touche utilisee : c'est lui qui deplace la
            # fenetre du tableau, donc lui qui pourrait deborder.
            for touche in range(len(P.PROFILES[nom])):
                ecran.surligner(touche, clock[0])
                clock[0] += 20
                ecran.tick(clock[0])

        # Le nom de fichier le plus long possible, avec le plus long des
        # abreges : c'est le pire cas de la ligne du bas.
        ecran.set_document('Blender|' + 'M' * 48)
        for _ in range(3000):
            ecran.tick(clock[0])
            clock[0] += 1

        ecran.config_screen('MACROPAD', 'macropad2026', '192.168.4.1')
        ecran.flush_startup()
        self.assertEqual(ecran.out_of_bounds if hasattr(ecran, 'out_of_bounds')
                         else ecran.oled.out_of_bounds, 0,
                         'debordement hors des 128x64 pixels')
        self.assertGreater(len(ecran.oled.pages), 8)



class PageWebDeConfiguration(unittest.TestCase):
    """Tests du serveur web du mode configuration, sans WiFi ni socket reel.

    On fabrique un faux client HTTP et on fait traiter de vraies requetes
    par le code du portail.
    """

    def setUp(self):
        clock[0] = 0
        try:
            import os
            os.remove(C.PROFILES_FILE)
        except OSError:
            pass

    tearDown = setUp

    class FauxClient:
        """Imite juste ce que portal.py utilise d'une socket."""

        def __init__(self, requete):
            self.entree = requete
            self.pos = 0
            self.sortie = b""

        def readline(self):
            fin = self.entree.find(b"\n", self.pos)
            if fin == -1:
                ligne = self.entree[self.pos:]
                self.pos = len(self.entree)
            else:
                ligne = self.entree[self.pos:fin + 1]
                self.pos = fin + 1
            return ligne

        def read(self, taille):
            bloc = self.entree[self.pos:self.pos + taille]
            self.pos += len(bloc)
            return bloc

        def write(self, data):
            self.sortie += data

        def settimeout(self, t):
            pass

        def close(self):
            pass

    def _requete(self, methode, chemin, corps=b""):
        import portal
        entete = "%s %s HTTP/1.1\r\nHost: 192.168.4.1\r\n" % (methode, chemin)
        if corps:
            entete += "Content-Length: %d\r\n" % len(corps)
        entete += "\r\n"
        client = self.FauxClient(entete.encode() + corps)
        portal.Portail(6)._traiter(client)
        return client.sortie

    def test_page_html_servie(self):
        sortie = self._requete("GET", "/")
        self.assertIn(b"200 OK", sortie)
        self.assertIn(b"text/html", sortie)
        self.assertIn(b"Macropad", sortie)
        self.assertIn(b"/api/profils", sortie)

    def test_api_renvoie_les_profils_usine(self):
        import json as J
        sortie = self._requete("GET", "/api/profils")
        self.assertIn(b"application/json", sortie)
        data = J.loads(sortie.split(b"\r\n\r\n", 1)[1])
        self.assertEqual(data["touches"], 6)
        self.assertEqual(data["origine"], "usine")
        self.assertEqual(data["ordre"], list(C.PROFILES_ORDER))
        civil = data["profils"]["CIVIL3D"]["touches"]
        self.assertEqual(len(civil), 6)
        self.assertEqual(civil[2]["court"]["valeur"], "_MATCHPROP")
        self.assertEqual(civil[2]["court"]["type"], "text_enter")
        # Les combinaisons sont lisibles dans le formulaire.
        self.assertEqual(civil[0]["court"]["valeur"], "CTRL+C")
        self.assertEqual(civil[0]["double"]["valeur"], "CTRL+V")
        self.assertEqual(civil[0]["long"]["valeur"], "CTRL+Z")
        # L'appui long de B3 retablit (Ctrl+Y).
        self.assertEqual(civil[2]["long"]["valeur"], "CTRL+Y")
        # La table des logiciels voyage avec la configuration.
        self.assertTrue(any(a["exe"] == "acad.exe"
                            for a in data["apps"]["liste"]))

    def test_enregistrement_valide(self):
        import json as J
        sortie = self._requete("GET", "/api/profils")
        data = J.loads(sortie.split(b"\r\n\r\n", 1)[1])
        data["profils"]["CIVIL3D"]["touches"][0] = {
            "label": "TALUS",
            "court": {"type": "text_enter", "valeur": "_GRADING"},
            "long": {"type": "combo", "valeur": "CTRL+S"},
            "double": {"type": "none", "valeur": ""}}
        reponse = self._requete("POST", "/api/profils",
                                J.dumps(data).encode())
        resultat = J.loads(reponse.split(b"\r\n\r\n", 1)[1])
        self.assertTrue(resultat["ok"], resultat.get("raison"))

        # La modification doit etre relue telle quelle par le firmware.
        import store
        profils, ordre, titres, couleurs, apps, repli, origine = store.charger(6)
        self.assertEqual(origine, "fichier")
        self.assertEqual(profils["CIVIL3D"][0][0], "TALUS")
        # L'appui long enregistre est bien relu.
        self.assertTrue(profils["CIVIL3D"][0][1].get("long"))
        frappes = compile_actions(profils["CIVIL3D"][0][1]["court"], "FR_AZERTY")
        self.assertEqual(len(frappes), len("_GRADING") + 1)   # + ENTREE
        self.assertEqual(frappes[0], (37,))                   # "_" en AZERTY

    def test_enregistrement_refuse_une_macro_intapable(self):
        import json as J
        sortie = self._requete("GET", "/api/profils")
        data = J.loads(sortie.split(b"\r\n\r\n", 1)[1])
        data["profils"]["WORD"]["touches"][0] = {
            "label": "KO",
            "court": {"type": "combo", "valeur": "CTRL+TOUCHE_BIDON"}}
        reponse = self._requete("POST", "/api/profils", J.dumps(data).encode())
        resultat = J.loads(reponse.split(b"\r\n\r\n", 1)[1])
        self.assertFalse(resultat["ok"])
        self.assertIn("WORD", resultat["raison"])
        # Rien ne doit avoir ete ecrit : on reste sur les profils d'usine.
        import store
        self.assertEqual(store.charger(6)[6], "usine")

    def test_enregistrement_refuse_un_json_casse(self):
        import json as J
        reponse = self._requete("POST", "/api/profils", b"{pas du json")
        resultat = J.loads(reponse.split(b"\r\n\r\n", 1)[1])
        self.assertFalse(resultat["ok"])

    def test_retour_usine(self):
        import store
        store.enregistrer(*store.defauts(), nb_touches=6)
        self.assertEqual(store.charger(6)[6], "fichier")
        self._requete("POST", "/api/usine")
        self.assertEqual(store.charger(6)[6], "usine")

    def test_chemin_inconnu(self):
        self.assertIn(b"404", self._requete("GET", "/nimportequoi"))



class LiaisonSerieAvecLePC(unittest.TestCase):
    """Tests du protocole serie : detection auto et configuration par USB."""

    class FausseSource:
        """Imite le port serie : on lui donne du texte, elle le rend."""

        def __init__(self):
            self.file = ""

        def envoyer(self, texte):
            self.file += texte

        def lire(self, maximum):
            morceau = self.file[:maximum]
            self.file = self.file[len(morceau):]
            return morceau

    def setUp(self):
        clock[0] = 0
        try:
            import os
            os.remove(C.PROFILES_FILE)
        except OSError:
            pass

    tearDown = setUp

    def _lien(self):
        import link
        source = self.FausseSource()
        sorties = []
        lien = link.Link(6, source=source, sortie=sorties.append)
        return lien, source, sorties

    # --- detection automatique -----------------------------------------
    def test_changement_de_profil_demande_par_le_pc(self):
        import link
        lien, source, _ = self._lien()
        source.envoyer("P:CIVIL3D\n")
        self.assertEqual(lien.service(), [(link.EVT_PROFIL, "CIVIL3D")])

    def test_nom_du_document(self):
        import link
        lien, source, _ = self._lien()
        source.envoyer("T:Projet_A12.dwg\n")
        self.assertEqual(lien.service(),
                         [(link.EVT_DOCUMENT, "Projet_A12.dwg")])
        self.assertEqual(lien.document, "Projet_A12.dwg")

    def test_ligne_coupee_en_deux_envois(self):
        # Le PC envoie souvent par morceaux : la ligne doit se reconstituer.
        import link
        lien, source, _ = self._lien()
        source.envoyer("P:BLEN")
        self.assertEqual(lien.service(), [])      # rien tant qu'il manque \n
        source.envoyer("DER\n")
        self.assertEqual(lien.service(), [(link.EVT_PROFIL, "BLENDER")])

    def test_lecture_bornee_par_tour_de_boucle(self):
        # Un gros envoi ne doit pas monopoliser la boucle principale :
        # au plus 256 caracteres sont lus par appel a service().
        lien, source, _ = self._lien()
        source.envoyer("x" * 1000 + "\n")
        lien.service()
        self.assertGreaterEqual(len(source.file), 1000 - 256)

    def test_commande_inconnue_ignoree(self):
        lien, source, sorties = self._lien()
        source.envoyer("BONJOUR\n?RIEN\n")
        self.assertEqual(lien.service(), [])
        self.assertEqual(sorties, [])

    def test_version(self):
        lien, source, sorties = self._lien()
        source.envoyer("?VER\n")
        lien.service()
        self.assertTrue(sorties[0].startswith("#VER:"))
        self.assertIn("FR_AZERTY", sorties[0])

    # --- lecture de la configuration par le PC --------------------------
    def test_le_pc_lit_la_configuration(self):
        import json as J
        lien, source, sorties = self._lien()
        source.envoyer("?CFG\n")
        lien.service()
        self.assertEqual(sorties[0], "#CFGBEGIN")
        self.assertEqual(sorties[-1], "#CFGEND")
        texte = "".join(l[3:] for l in sorties if l.startswith("#C:"))
        data = J.loads(texte)
        self.assertEqual(data["touches"], 6)
        self.assertEqual(data["ordre"], list(C.PROFILES_ORDER))
        self.assertEqual(
            data["profils"]["CIVIL3D"]["touches"][2]["court"]["valeur"],
            "_MATCHPROP")

    # --- ecriture de la configuration par le PC -------------------------
    def _envoyer_config(self, lien, source, data):
        import json as J
        texte = J.dumps(data)
        source.envoyer("!CFGBEGIN\n")
        for debut in range(0, len(texte), 60):
            source.envoyer("!C:" + texte[debut:debut + 60] + "\n")
        source.envoyer("!CFGEND\n")
        evenements = []
        for _ in range(200):          # plusieurs tours, lecture bornee
            evenements += list(lien.service())
        return evenements

    def test_le_pc_ecrit_la_configuration(self):
        import json as J, link, store
        lien, source, sorties = self._lien()
        source.envoyer("?CFG\n")
        lien.service()
        data = J.loads("".join(l[3:] for l in sorties if l.startswith("#C:")))
        data["profils"]["CIVIL3D"]["touches"][0] = {
            "label": "TALUS",
            "court": {"type": "text_enter", "valeur": "_GRADING"},
            "long": {"type": "combo", "valeur": "CTRL+S"},
            "double": {"type": "none", "valeur": ""}}

        sorties.clear()
        evenements = self._envoyer_config(lien, source, data)
        self.assertIn((link.EVT_RECHARGER, None), evenements)
        self.assertTrue(any(s.startswith("#OK:") for s in sorties), sorties)

        profils, ordre, titres, couleurs, apps, repli, origine = store.charger(6)
        self.assertEqual(origine, "fichier")
        self.assertEqual(profils["CIVIL3D"][0][0], "TALUS")
        # L'appui long enregistre est bien relu.
        self.assertTrue(profils["CIVIL3D"][0][1].get("long"))

    def test_macro_intapable_refusee_par_le_lien(self):
        import json as J, link, store
        lien, source, sorties = self._lien()
        source.envoyer("?CFG\n")
        lien.service()
        data = J.loads("".join(l[3:] for l in sorties if l.startswith("#C:")))
        data["profils"]["WORD"]["touches"][0] = {
            "label": "KO",
            "court": {"type": "combo", "valeur": "CTRL+TOUCHE_BIDON"}}

        sorties.clear()
        evenements = self._envoyer_config(lien, source, data)
        self.assertNotIn((link.EVT_RECHARGER, None), evenements)
        self.assertTrue(any(s.startswith("#KO:") for s in sorties), sorties)
        # Rien n'a ete ecrit : on reste sur les profils d'usine.
        self.assertEqual(store.charger(6)[6], "usine")

    def test_json_casse_refuse(self):
        lien, source, sorties = self._lien()
        source.envoyer("!CFGBEGIN\n!C:{pas du json\n!CFGEND\n")
        for _ in range(20):
            lien.service()
        self.assertTrue(any(s.startswith("#KO:") for s in sorties), sorties)

    def test_rechargement_demande(self):
        import link
        lien, source, sorties = self._lien()
        source.envoyer("!RELOAD\n")
        self.assertEqual(lien.service(), [(link.EVT_RECHARGER, None)])
        self.assertTrue(sorties[0].startswith("#OK:"))

    def test_configuration_trop_volumineuse_refusee(self):
        lien, source, sorties = self._lien()
        source.envoyer("!CFGBEGIN\n")
        for _ in range(80):
            source.envoyer("!C:" + "x" * 150 + "\n")
        for _ in range(400):
            lien.service()
        self.assertTrue(any("volumineuse" in s for s in sorties), sorties)



class GestesCourtLongDouble(unittest.TestCase):
    """Appui court, appui long et double appui."""

    def setUp(self):
        clock[0] = 0
        from gestures import Gestes
        self.G = Gestes(6, long_ms=400, double_ms=260)

    def _touche(self, index, long_=False, double=False):
        self.G.a_long[index] = long_
        self.G.a_double[index] = double

    # --- appui court -----------------------------------------------------
    def test_appui_court_instantane_sans_double(self):
        # Une touche SANS macro double ne doit subir aucun retard.
        self._touche(0)
        self.assertIsNone(self.G.appui(0, 0))
        self.assertEqual(self.G.relachement(0, 80), 'court')
        self.assertEqual(self.G.service(80), [])

    def test_appui_court_retarde_si_double_possible(self):
        # Avec une macro double, il faut bien attendre de savoir.
        self._touche(0, double=True)
        self.G.appui(0, 0)
        self.assertIsNone(self.G.relachement(0, 80))     # on ne conclut pas
        self.assertEqual(self.G.service(200), [])        # toujours dans le delai
        self.assertEqual(self.G.service(345), [(0, 'court')])

    # --- double appui ----------------------------------------------------
    def test_double_appui(self):
        self._touche(0, double=True)
        self.G.appui(0, 0)
        self.G.relachement(0, 60)
        self.assertEqual(self.G.appui(0, 150), 'double')
        self.assertEqual(self.G.service(500), [])        # pas de court en plus

    def test_deux_appuis_trop_espaces_font_deux_courts(self):
        self._touche(0, double=True)
        self.G.appui(0, 0)
        self.G.relachement(0, 60)
        self.assertEqual(self.G.service(330), [(0, 'court')])
        self.G.appui(0, 400)
        self.G.relachement(0, 460)
        self.assertEqual(self.G.service(730), [(0, 'court')])

    # --- appui long ------------------------------------------------------
    def test_appui_long_part_des_le_seuil(self):
        self._touche(0, long_=True)
        self.G.appui(0, 0)
        self.assertEqual(self.G.service(399), [])
        self.assertEqual(self.G.service(400), [(0, 'long')])
        # Le relachement ne doit PAS declencher un court en plus.
        self.assertIsNone(self.G.relachement(0, 900))

    def test_maintien_sans_macro_longue_reste_un_court(self):
        self._touche(0)                      # aucune macro longue
        self.G.appui(0, 0)
        self.assertEqual(self.G.service(2000), [])
        self.assertEqual(self.G.relachement(0, 2000), 'court')

    def test_touches_independantes(self):
        self._touche(0, long_=True)
        self._touche(1, double=True)
        self.G.appui(0, 0)
        self.G.appui(1, 10)
        self.G.relachement(1, 60)
        # La touche 1 conclut son attente de double a t=320.
        self.assertEqual(self.G.service(330), [(1, 'court')])
        self.assertEqual(self.G.service(399), [])
        # La touche 0, elle, franchit son seuil long a t=400.
        self.assertEqual(self.G.service(400), [(0, 'long')])
        self.assertEqual(self.G.service(500), [])

    def test_configurer_depuis_les_macros(self):
        import profiles as P
        self.G.configurer(P.PROFILES['CIVIL3D'])
        # B3 MATCH a un appui long (retablir), pas de double.
        self.assertTrue(self.G.a_long[2])
        self.assertFalse(self.G.a_double[2])
        # B5 ZOOM a un double appui.
        self.assertTrue(self.G.a_double[4])
        # B1 est le presse-papiers : les trois gestes sont occupes.
        self.assertTrue(self.G.a_long[0])
        self.assertTrue(self.G.a_double[0])
        # B4 ISOLE n'a pas de double appui : aucun retard, aucune
        # attente. C'est ce qui garde les touches instantanees.
        self.assertFalse(self.G.a_double[3])
        # B2 est la touche modificatrice : mode a part.
        self.assertTrue(self.G.a_maintien[1])
        self.assertTrue(self.G.a_maintien2[1])
        self.assertFalse(self.G.a_maintien[0])


class ToucheModificatrice(unittest.TestCase):
    """Une touche qui fait Ctrl et Maj, comme sur un vrai clavier.

    Demande : un appui maintenu donne Ctrl ; un appui bref suivi d'un
    appui maintenu donne Maj. Le modificateur doit rester enfonce cote PC
    tant que le doigt reste sur la touche, pour pouvoir cliquer a la
    souris pendant ce temps.
    """

    def setUp(self):
        clock[0] = 0
        from gestures import Gestes, COURT, LONG, DOUBLE, FIN
        self.COURT, self.LONG, self.DOUBLE, self.FIN = COURT, LONG, DOUBLE, FIN
        self.G = Gestes(6, long_ms=400, double_ms=260)
        self.G.configurer([
            ("CTRL", {COURT: [("maintien", ("CTRL",))],
                      DOUBLE: [("maintien", ("SHIFT",))]}),
            ("SIMPLE", {COURT: [("key", "F5")]}),
            ("SEUL", {COURT: [("maintien", ("ALT",))]}),
            ("", {}), ("", {}), ("", {}),
        ])

    # --- la machine a etats -------------------------------------------
    def test_appui_maintenu_donne_le_premier_modificateur(self):
        # Le modificateur part DES l'appui : aucune attente.
        self.assertEqual(self.G.appui(0, 0), self.COURT)
        self.assertEqual(self.G.service(100), [])
        self.assertEqual(self.G.service(500), [])   # meme au-dela du long
        self.assertEqual(self.G.relachement(0, 600), self.FIN)

    def test_bref_puis_maintenu_donne_le_second(self):
        self.assertEqual(self.G.appui(0, 0), self.COURT)
        self.assertEqual(self.G.relachement(0, 60), self.FIN)
        # Second appui dans la fenetre : c'est Maj.
        self.assertEqual(self.G.appui(0, 200), self.DOUBLE)
        self.assertEqual(self.G.relachement(0, 900), self.FIN)
        # Et on est bien revenu au depart.
        self.assertEqual(self.G.appui(0, 1000), self.COURT)

    def test_second_appui_trop_tard_redonne_le_premier(self):
        self.G.appui(0, 0)
        self.G.relachement(0, 60)
        self.assertEqual(self.G.service(400), [])   # la fenetre expire
        self.assertEqual(self.G.appui(0, 500), self.COURT)

    def test_touche_a_un_seul_maintien(self):
        self.assertEqual(self.G.appui(2, 0), self.COURT)
        self.assertEqual(self.G.relachement(2, 50), self.FIN)
        # Pas de second maintien : l'appui suivant repart sur le premier.
        self.assertEqual(self.G.appui(2, 100), self.COURT)

    def test_les_autres_touches_ne_changent_pas(self):
        self.assertIsNone(self.G.appui(1, 0))
        self.assertEqual(self.G.relachement(1, 50), self.COURT)

    # --- le clavier ----------------------------------------------------
    # Rappel : pump(k, depart, duree) fait avancer l'horloge de "depart" a
    # "depart + duree", par pas de 2 ms - comme la vraie boucle.
    def test_le_modificateur_reste_enfonce(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.maintenir([("maintien", ("CTRL",))])
        pump(k, 10, 40)
        # Ctrl seul, et il reste dans le rapport.
        self.assertIn((-1,), t.sent)
        self.assertEqual(t.sent[-1], (-1,))

    def test_une_macro_pendant_le_maintien_garde_le_modificateur(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.maintenir([("maintien", ("CTRL",))])
        pump(k, 10, 40)
        k.submit([("key", "F5")])
        pump(k, 60, 120)
        # F5 (62) est parti AVEC Ctrl : c'est bien Ctrl+F5 qu'a recu le PC.
        self.assertIn((-1, 62), t.sent)
        # Et entre les frappes, Ctrl n'est jamais remonte : aucun rapport
        # vide tant que le doigt tient la touche.
        self.assertEqual(t.sent[-1], (-1,))
        self.assertNotIn((), t.sent[1:])

    def test_relachement_libere_le_modificateur(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.maintenir([("maintien", ("CTRL",))])
        pump(k, 10, 40)
        k.relacher_maintien()
        pump(k, 60, 40)
        self.assertEqual(t.sent[-1], ())
        self.assertFalse(k.keys_down)

    def test_esc_libere_un_modificateur_bloque(self):
        # Le pire scenario : Ctrl enfonce et quelque chose qui derape.
        # ESC doit TOUT relacher, sinon le PC reste avec Ctrl coince.
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.maintenir([("maintien", ("CTRL",))])
        pump(k, 10, 40)
        k.escape(60)
        pump(k, 62, 200)
        self.assertEqual(k.tenus, ())
        self.assertIn((41,), t.sent)          # Echap est bien parti
        self.assertEqual(t.sent[-1], ())

    def test_changement_de_profil_libere_le_modificateur(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.maintenir([("maintien", ("CTRL",))])
        pump(k, 10, 40)
        k.cancel()                            # ce que fait un changement
        pump(k, 60, 40)
        self.assertEqual(k.tenus, ())
        self.assertEqual(t.sent[-1], ())

    def test_deconnexion_usb_oublie_le_maintien(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.maintenir([("maintien", ("CTRL",))])
        pump(k, 10, 40)
        t.open = False
        k.tick(60)
        self.assertEqual(k.tenus, ())

    def test_maintien_intapable_refuse_sans_rien_envoyer(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        with self.assertRaises(ValueError):
            k.maintenir([("maintien", ("TOUCHE_BIDON",))])
        self.assertEqual(k.tenus, ())

    # --- la configuration ----------------------------------------------
    def test_aller_retour_par_la_page_web(self):
        import store
        entree = store.action_vers_json([("maintien", ("CTRL",))])
        self.assertEqual(entree, ("maintien", "CTRL"))
        self.assertEqual(store.action_depuis_json("maintien", "CTRL"),
                         [("maintien", ("CTRL",))])
        self.assertEqual(store.action_depuis_json("maintien", "CTRL+SHIFT"),
                         [("maintien", ("CTRL", "SHIFT"))])

    def test_les_valeurs_usine_de_civil3d(self):
        import profiles as P
        import store
        label, gestes = P.PROFILES["CIVIL3D"][1]
        self.assertEqual(label, "CTRL")
        self.assertEqual(gestes["court"], [("maintien", ("CTRL",))])
        self.assertEqual(gestes["double"], [("maintien", ("SHIFT",))])
        # Et elles restent verifiables comme n'importe quelle macro.
        self.assertEqual(store.verifier({"CIVIL3D": P.PROFILES["CIVIL3D"]},
                                        ["CIVIL3D"], 6), [])


class CouleursDesProfils(unittest.TestCase):
    """La couleur des LED voyage avec la configuration.

    Elle est rangee dans profils.json et modifiable depuis les deux pages
    web : ajouter un logiciel, c'est aussi lui donner sa couleur, sans
    toucher a config.py.
    """

    def setUp(self):
        try:
            import os
            os.remove(C.PROFILES_FILE)
        except OSError:
            pass

    tearDown = setUp

    def test_conversion_dans_les_deux_sens(self):
        import store
        self.assertEqual(store.couleur_vers_texte((0, 160, 255)), "#00a0ff")
        self.assertEqual(store.couleur_depuis_texte("#00A0FF"), (0, 160, 255))
        self.assertEqual(store.couleur_depuis_texte("00a0ff"), (0, 160, 255))

    def test_une_couleur_illisible_ne_bloque_pas_l_enregistrement(self):
        # Une couleur fausse ne doit pas faire perdre des macros valables :
        # on retombe sur la couleur d'usine, et c'est tout.
        import store
        usine = store.couleur_usine("CIVIL3D")
        for mauvaise in ("", None, "bleu", "#12", "#zzzzzz", 42):
            self.assertEqual(store.couleur_depuis_texte(mauvaise, usine),
                             usine, repr(mauvaise))

    def test_les_couleurs_usine_viennent_de_config(self):
        import store
        _, _, _, couleurs, _, _ = store.defauts()
        self.assertEqual(couleurs["CIVIL3D"], tuple(C.RGB_COULEURS["CIVIL3D"]))
        self.assertEqual(couleurs["BLENDER"], tuple(C.RGB_COULEURS["BLENDER"]))

    def test_la_page_web_recoit_les_couleurs(self):
        import store
        data = store.vers_json(6)
        self.assertEqual(data["profils"]["CIVIL3D"]["couleur"],
                         store.couleur_vers_texte(C.RGB_COULEURS["CIVIL3D"]))

    def test_une_couleur_choisie_survit_a_l_enregistrement(self):
        import store
        data = store.vers_json(6)
        data["profils"]["WORD"]["couleur"] = "#123456"
        ok, raison = store.enregistrer_json(data, 6)
        self.assertTrue(ok, raison)

        _, _, _, couleurs, _, _, origine = store.charger(6)
        self.assertEqual(origine, "fichier")
        self.assertEqual(couleurs["WORD"], (0x12, 0x34, 0x56))
        # Les autres n'ont pas bouge.
        self.assertEqual(couleurs["CIVIL3D"], tuple(C.RGB_COULEURS["CIVIL3D"]))
        # Et la page web la relit telle quelle.
        self.assertEqual(store.vers_json(6)["profils"]["WORD"]["couleur"],
                         "#123456")

    def test_un_ancien_fichier_sans_couleur_prend_celles_d_usine(self):
        # profils.json ecrit avant les LED RGB : aucune couleur dedans.
        import store
        data = store.vers_json(6)
        for bloc in data["profils"].values():
            del bloc["couleur"]
        ok, raison = store.enregistrer_json(data, 6)
        self.assertTrue(ok, raison)
        _, _, _, couleurs, _, _, _ = store.charger(6)
        self.assertEqual(couleurs["CIVIL3D"], tuple(C.RGB_COULEURS["CIVIL3D"]))


class LedsRgb(unittest.TestCase):
    """Les LED RGB des touches, sans LED.

    Le test le plus important de ce fichier est le premier : il verifie
    que le plafond de luminosite est bien applique. Sans lui, six LED en
    blanc a fond tirent 360 mA, le 5 V du port USB s'effondre et la carte
    redemarre en pleine frappe.
    """

    def setUp(self):
        clock[0] = 0
        # Faux neopixel : il retient ce qu'on lui ecrit.
        module = types.ModuleType('neopixel')

        class NeoPixel:
            def __init__(self, pin, n):
                self.pin, self.n = pin, n
                self.pixels = [(0, 0, 0)] * n
                self.ecritures = 0

            def __setitem__(self, index, valeur):
                self.pixels[index] = valeur

            def __getitem__(self, index):
                return self.pixels[index]

            def write(self):
                self.ecritures += 1

        module.NeoPixel = NeoPixel
        sys.modules['neopixel'] = module

        self.sauvegarde = {}
        # Respiration eteinte par defaut dans ces tests : elle fait
        # varier la luminosite en permanence, ce qui empeche de comparer
        # une couleur a une valeur exacte. Elle a ses propres tests.
        self._regler(RGB_ENABLED=True, RGB_TYPE="WS2812", RGB_PIN=16,
                     RGB_COUNT=6, RGB_ORDRE="GRB", RGB_LUMINOSITE=40,
                     RGB_VEILLE_MS=300000, RGB_MS=25,
                     RGB_RESPIRATION=False)

    def tearDown(self):
        for nom, valeur in self.sauvegarde.items():
            setattr(C, nom, valeur)

    def _regler(self, **valeurs):
        for nom, valeur in valeurs.items():
            if nom not in self.sauvegarde:
                self.sauvegarde[nom] = getattr(C, nom, None)
            setattr(C, nom, valeur)

    def _rgb(self):
        import rgb
        objet = rgb.Rgb()
        self.assertTrue(objet.actif, "les LED auraient du s'initialiser")
        return objet

    # --- LA securite --------------------------------------------------
    def test_la_luminosite_plafonne_vraiment_le_courant(self):
        import rgb
        self.assertEqual(rgb.limiter((255, 255, 255)), (40, 40, 40))
        self.assertEqual(rgb.limiter((0, 0, 0)), (0, 0, 0))
        # Meme une couleur aberrante reste dans les clous.
        self.assertEqual(rgb.limiter((999, -20, 128)), (40, 0, 20))

        # Le calcul qui compte : 60 mA par LED en blanc plein. Avec le
        # plafond livre, six LED restent tres en dessous des 500 mA de
        # l'USB, marge confortable pour la carte et l'ecran.
        pire = rgb.limiter((255, 255, 255))
        courant = 6 * 60 * sum(pire) / (3 * 255.0)
        self.assertLess(courant, 100,
                        "six LED tireraient %d mA : trop pour l'USB" % courant)

    def test_aucun_acces_materiel_quand_c_est_desactive(self):
        self._regler(RGB_ENABLED=False)
        import rgb
        objet = rgb.Rgb()
        self.assertFalse(objet.actif)
        self.assertIsNone(objet.materiel)
        objet.profil(C.RGB_COULEURS["CIVIL3D"]); objet.touche(0, 0); objet.tick(0)
        objet.close()          # rien ne doit lever

    # --- les couleurs --------------------------------------------------
    def test_chaque_profil_a_sa_couleur(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["CIVIL3D"])
        objet.tick(100)
        attendu = tuple(C.RGB_COULEURS["CIVIL3D"])
        import rgb
        r, v, b = rgb.limiter(attendu)
        # Les WS2812 attendent VERT, ROUGE, BLEU.
        for pixel in objet.materiel.pixels:
            self.assertEqual(pixel, (v, r, b))

    def test_ordre_des_couleurs_configurable(self):
        self._regler(RGB_ORDRE="RGB")
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["CIVIL3D"])
        objet.tick(100)
        import rgb
        r, v, b = rgb.limiter(C.RGB_COULEURS["CIVIL3D"])
        self.assertEqual(objet.materiel.pixels[0], (r, v, b))

    def test_profil_inconnu_prend_la_couleur_par_defaut(self):
        objet = self._rgb()
        objet.profil(None)
        objet.tick(100)
        import rgb
        r, v, b = rgb.limiter(C.RGB_COULEUR_DEFAUT)
        self.assertEqual(objet.materiel.pixels[0], (v, r, b))

    def test_la_touche_utilisee_passe_en_blanc(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        objet.tick(100)
        objet.touche(3, 200)
        objet.tick(300)
        import rgb
        blanc = rgb.limiter((255, 255, 255))
        fond = rgb.limiter(C.RGB_COULEURS["WORD"])
        self.assertEqual(objet.materiel.pixels[3], blanc)
        self.assertNotEqual(objet.materiel.pixels[2], blanc)
        r, v, b = fond
        self.assertEqual(objet.materiel.pixels[2], (v, r, b))

        # Puis elle revient a la couleur du profil.
        objet.tick(300 + C.HIGHLIGHT_MS + 50)
        self.assertEqual(objet.materiel.pixels[3], (v, r, b))

    def test_panne_hid_passe_au_rouge_et_revient(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["BLENDER"])
        objet.tick(100)
        objet.etat("ERR")
        objet.tick(200)
        import rgb
        r, v, b = rgb.limiter(C.RGB_COULEUR_ERREUR)
        self.assertEqual(objet.materiel.pixels[0], (v, r, b))
        objet.etat("HID")
        objet.tick(300)
        r, v, b = rgb.limiter(C.RGB_COULEURS["BLENDER"])
        self.assertEqual(objet.materiel.pixels[0], (v, r, b))

    # --- veille et cadence ---------------------------------------------
    def test_extinction_apres_la_veille_puis_reveil(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        objet.tick(100)
        objet.tick(100 + C.RGB_VEILLE_MS + 10)
        self.assertEqual(objet.materiel.pixels[0], (0, 0, 0))
        # Le premier appui rallume.
        objet.touche(0, 100 + C.RGB_VEILLE_MS + 20)
        objet.tick(100 + C.RGB_VEILLE_MS + 60)
        self.assertNotEqual(objet.materiel.pixels[0], (0, 0, 0))

    def test_pas_plus_d_un_envoi_par_periode(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        objet.tick(0)
        depart = objet.materiel.ecritures
        # Cent tours de boucle, soit 100 ms de temps simule : a la
        # cadence livree (un envoi toutes les 25 ms), cela doit faire
        # quatre ou cinq envois, pas cent. Envoyer a chaque tour
        # occuperait le processeur pour rien - et les WS2812 coupent les
        # interruptions pendant l'envoi.
        for n in range(100):
            objet.touche(n % 6, n)
            objet.tick(n)
        envois = objet.materiel.ecritures - depart
        self.assertLessEqual(envois, 100 // C.RGB_MS + 1)
        self.assertGreater(envois, 0)

    def test_rien_a_envoyer_rien_n_est_envoye(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        objet.tick(0)
        depart = objet.materiel.ecritures
        for n in range(1000, 3000, 2):
            objet.tick(n)
        self.assertEqual(objet.materiel.ecritures, depart)

    # --- la respiration --------------------------------------------------
    def test_la_courbe_de_respiration(self):
        """Meme courbe que la LED du bouton ESC : douce aux extremites."""
        import rgb
        self._regler(RGB_RESPIRATION_MS=4000, RGB_RESPIRATION_MIN=0.35)
        creux = rgb.respiration(0)
        milieu = rgb.respiration(2000)
        self.assertAlmostEqual(creux, 0.35, places=3)
        self.assertAlmostEqual(milieu, 1.0, places=3)
        # Elle monte sans a-coup, et repart au creux au cycle suivant.
        precedent = creux
        for phase in range(0, 2001, 100):
            valeur = rgb.respiration(phase)
            self.assertGreaterEqual(valeur + 1e-9, precedent)
            precedent = valeur
        self.assertAlmostEqual(rgb.respiration(4000), creux, places=3)
        # Et elle ne descend jamais sous le plancher : le pad ne s'eteint
        # pas au creux, il faiblit seulement.
        for phase in range(0, 4000, 37):
            self.assertGreaterEqual(rgb.respiration(phase), 0.35 - 1e-9)

    def test_la_couleur_respire_vraiment(self):
        self._regler(RGB_RESPIRATION=True, RGB_RESPIRATION_MS=4000)
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["CIVIL3D"])
        vues = []
        for instant in range(0, 4000, 100):
            objet.tick(instant)
            vues.append(objet.materiel.pixels[0])
        # La luminosite doit varier, et repasser par un creux et un sommet.
        sommes = [sum(v) for v in vues]
        self.assertGreater(max(sommes), min(sommes),
                           "la couleur ne respire pas")
        # Toujours la meme teinte : c'est la LUMINOSITE qui varie, pas la
        # couleur. Le vert reste devant le rouge, qui reste devant le bleu.
        for vert, rouge, bleu in vues:
            if rouge or vert or bleu:
                self.assertLessEqual(rouge, vert + 1)

    def test_respiration_eteinte_laisse_la_couleur_fixe(self):
        objet = self._rgb()          # setUp a mis RGB_RESPIRATION=False
        objet.profil(C.RGB_COULEURS["CIVIL3D"])
        objet.tick(0)
        premiere = objet.materiel.pixels[0]
        for instant in range(100, 4000, 100):
            objet.tick(instant)
        self.assertEqual(objet.materiel.pixels[0], premiere)

    def test_la_touche_utilisee_ne_respire_pas(self):
        # Le retour visuel doit etre franc : la touche pressee est en
        # blanc plein, pas en blanc qui palpite.
        self._regler(RGB_RESPIRATION=True)
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        import rgb
        blanc = rgb.limiter((255, 255, 255))
        for instant in range(0, 800, 100):
            objet.touche(2, instant)
            objet.tick(instant)
            self.assertEqual(objet.materiel.pixels[2], blanc)

    def test_l_horloge_qui_saute_ne_fait_pas_sauter_la_couleur(self):
        # Un tour de boucle tres long (garbage collector, ecriture flash)
        # ne doit pas propulser la respiration a l'autre bout du cycle.
        self._regler(RGB_RESPIRATION=True, RGB_RESPIRATION_MS=4000)
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        objet.tick(0)
        phase = objet._phase
        objet.tick(60000)            # une minute d'un coup
        self.assertEqual(objet._phase, phase)

    # --- robustesse ------------------------------------------------------
    def test_materiel_absent_ne_plante_pas(self):
        del sys.modules['neopixel']
        import rgb
        objet = rgb.Rgb()
        self.assertFalse(objet.actif)
        objet.profil(C.RGB_COULEURS["WORD"]); objet.touche(0, 0); objet.tick(0); objet.close()

    def test_panne_en_cours_de_route_desactive_sans_remonter(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])

        def casse():
            raise OSError("fil arrache")
        objet.materiel.write = casse
        objet.tick(100)            # ne doit rien lever
        self.assertFalse(objet.actif)

    def test_tout_s_eteint_a_l_arret(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        objet.tick(100)
        objet.close()
        self.assertEqual(objet.materiel.pixels[0], (0, 0, 0))
        self.assertFalse(objet.actif)

    # --- le montage a une seule LED RGB ---------------------------------
    def test_montage_pwm_anode_commune(self):
        self._regler(RGB_TYPE="PWM", RGB_PIN_R=16, RGB_PIN_V=17,
                     RGB_PIN_B=18, RGB_ANODE_COMMUNE=True)
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["CIVIL3D"])
        objet.tick(100)
        import rgb
        r, v, b = rgb.limiter(C.RGB_COULEURS["CIVIL3D"])
        # Anode commune : le GPIO tire vers le bas, donc c'est inverse.
        self.assertEqual(objet.materiel[0].values[-1], 65535 - r * 257)
        self.assertEqual(objet.materiel[1].values[-1], 65535 - v * 257)
        self.assertEqual(objet.materiel[2].values[-1], 65535 - b * 257)

    def test_montage_pwm_cathode_commune(self):
        self._regler(RGB_TYPE="PWM", RGB_PIN_R=16, RGB_PIN_V=17,
                     RGB_PIN_B=18, RGB_ANODE_COMMUNE=False)
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["CIVIL3D"])
        objet.tick(100)
        import rgb
        r, v, b = rgb.limiter(C.RGB_COULEURS["CIVIL3D"])
        self.assertEqual(objet.materiel[0].values[-1], r * 257)


class ValeursUsineSansPiege(unittest.TestCase):
    """Les valeurs d'usine doivent survivre a un aller-retour par page web."""

    def setUp(self):
        try:
            import os
            os.remove(C.PROFILES_FILE)
        except OSError:
            pass

    tearDown = setUp

    def test_aucune_sequence_dans_les_valeurs_usine(self):
        # Les pages web ne gardent qu'UNE action par geste. Si une valeur
        # d'usine en contenait deux, un simple "Enregistrer" la tronquerait
        # sans prevenir. On interdit donc le piege a la source.
        import profiles as P
        for nom, touches in P.PROFILES.items():
            for index, (label, gestes) in enumerate(touches):
                for geste, actions in gestes.items():
                    self.assertEqual(
                        len(actions), 1,
                        "%s B%d %s : %d actions, la page web n'en garderait "
                        "qu'une" % (nom, index + 1, geste, len(actions)))

    def test_aller_retour_complet_sans_perte(self):
        import store
        avant = store.vers_json(6)
        ok, raison = store.enregistrer_json(avant, 6)
        self.assertTrue(ok, raison)
        apres = store.vers_json(6)
        self.assertEqual(apres["ordre"], avant["ordre"])
        self.assertEqual(apres["apps"], avant["apps"])
        for nom in avant["ordre"]:
            self.assertEqual(apres["profils"][nom], avant["profils"][nom], nom)


class PageDeConfigurationIntacte(unittest.TestCase):
    """La page web est ecrite une seule fois, dans tools/page_config.html,
    puis recopiee dans les deux serveurs par tools/injecter_page.py.

    Ces tests existent a cause d'un bug reel : la page etait recopiee dans
    une chaine Python ORDINAIRE, ou l'antislash est un caractere
    d'echappement. Le \\n d'un message JavaScript devenait un vrai passage
    a la ligne, la chaine JavaScript n'etait plus fermee, et le navigateur
    refusait TOUT le script. Resultat : une page qui s'affiche mais reste
    vide, sans aucun message d'erreur visible. Impossible a deviner.
    """

    def setUp(self):
        import re
        self.re = re
        self.source = (ROOT / "tools" / "page_config.html").read_text(
            encoding="utf-8").rstrip("\n")

    def _page_du_fichier(self, chemin):
        """Relit la page telle que Python la comprendra reellement."""
        texte = chemin.read_text(encoding="utf-8")
        trouve = self.re.search(r"PAGE = (r?\"\"\".*?\"\"\")", texte, self.re.S)
        self.assertIsNotNone(trouve, "PAGE introuvable dans %s" % chemin.name)
        return ast.literal_eval(trouve.group(1)).rstrip("\n")

    def test_portail_wifi_sert_la_page_source(self):
        self.assertEqual(self._page_du_fichier(ROOT / "device" / "portal.py"),
                         self.source,
                         "device/portal.py a divergé : relance "
                         "python3 tools/injecter_page.py")

    def test_compagnon_pc_sert_la_meme_page(self):
        self.assertEqual(
            self._page_du_fichier(ROOT / "pc" / "macropad_auto.py"),
            self.source,
            "pc/macropad_auto.py a divergé : relance "
            "python3 tools/injecter_page.py")

    def test_le_javascript_de_la_page_est_valide(self):
        """Le controle qui aurait evite le bug : le script se lit-il ?"""
        node = shutil.which("node") or shutil.which("nodejs")
        if not node:
            self.skipTest("node absent : verification syntaxique impossible")
        script = self.re.search(r"<script>(.*?)</script>", self.source,
                                self.re.S)
        self.assertIsNotNone(script, "la page n'a plus de bloc <script>")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as fichier:
            fichier.write(script.group(1))
            chemin = fichier.name
        try:
            resultat = subprocess.run([node, "--check", chemin],
                                      capture_output=True, text=True)
        finally:
            os.remove(chemin)
        self.assertEqual(resultat.returncode, 0,
                         "JavaScript invalide :\n" + resultat.stderr)

    # ------------------------------------------------------------------
    def _construire(self, configuration):
        """Fait tourner la page hors navigateur et retourne ce qu'elle a
        fabrique. Voir tests/page_smoke.js pour le detail."""
        node = shutil.which("node") or shutil.which("nodejs")
        if not node:
            self.skipTest("node absent : rendu de la page non verifiable")
        script = self.re.search(r"<script>(.*?)</script>", self.source,
                                self.re.S).group(1)
        dossier = tempfile.mkdtemp()
        chemin_js = os.path.join(dossier, "page.js")
        chemin_cfg = os.path.join(dossier, "cfg.json")
        with open(chemin_js, "w", encoding="utf-8") as fichier:
            fichier.write(script)
        with open(chemin_cfg, "w", encoding="utf-8") as fichier:
            json.dump(configuration, fichier)
        resultat = subprocess.run(
            [node, str(ROOT / "tests" / "page_smoke.js"), chemin_js,
             chemin_cfg], capture_output=True, text=True)
        self.assertEqual(resultat.returncode, 0,
                         "la page n'a pas su se construire :\n"
                         + resultat.stdout + resultat.stderr)
        return json.loads(resultat.stdout.strip().split("\n")[-1])

    def test_la_page_se_construit_avec_de_vraies_donnees(self):
        """Le controle qui compte vraiment : la page se dessine-t-elle ?

        Une page dont le script plante en cours de route s'affiche vide,
        sans le moindre message. On lui donne donc les valeurs d'usine et
        on compte ce qu'elle a produit."""
        import store
        configuration = store.vers_json(6)
        vu = self._construire(configuration)

        profils = len(configuration["ordre"])
        self.assertEqual(vu["cartes"], profils)
        # Une liste deroulante par geste : 6 touches x 3 gestes par profil.
        self.assertEqual(vu["listes"], profils * 6 * 3)
        self.assertIn("source", vu["src"])
        self.assertIn("appuis", vu["cnt"])
        # Les logiciels : une ligne d'en-tete, une par logiciel, une pour
        # le repli.
        self.assertEqual(vu["apps"],
                         len(configuration["apps"]["liste"]) + 2)
        self.assertFalse(vu["texte_vide"])

    def test_une_saisie_va_bien_sur_la_touche_ou_on_la_tape(self):
        """Le deuxieme bug reel : tout finissait sur la derniere touche.

        En JavaScript, « var » appartient a la fonction et non au bloc.
        La variable de boucle etait donc partagee par les six touches, et
        chaque champ modifiait la derniere. A l'ecran tout paraissait
        normal - le texte tape s'affiche bien dans la case - mais rien
        n'arrivait a la bonne touche.

        Le test tape dans le libelle et dans la valeur de la touche 1,
        modifie l'abrege du deuxieme logiciel, enregistre, et regarde ce
        qui part reellement sur le port serie."""
        import store
        vu = self._construire(store.vers_json(6))

        self.assertTrue(vu["envoye"], "l'enregistrement n'a rien envoye")
        self.assertEqual(vu["touche1_label"], "ZZZ")
        self.assertEqual(vu["touche1_valeur"], "TESTVAL")
        # La touche 6 ne doit surtout pas avoir bouge.
        self.assertEqual(vu["derniere_touche_label"], "MOVE")
        # Meme verification sur la table des logiciels.
        self.assertEqual(vu["app2_abrege"], "AbRg")
        self.assertEqual(vu["app1_abrege"], "C3D")
        self.assertIn("Enregistre", vu["message"])

    def test_la_couleur_des_led_se_choisit_par_profil(self):
        """Un selecteur de couleur par profil, et il vise le bon profil."""
        import store
        configuration = store.vers_json(6)
        vu = self._construire(configuration)

        # Un carre de couleur par profil, dans l'en-tete de sa carte.
        self.assertEqual(vu["couleurs"], 1)
        # La couleur choisie part bien avec le premier profil...
        self.assertEqual(vu["couleur1"], "#123456")
        # ...et le profil suivant garde la sienne.
        deuxieme = configuration["ordre"][1]
        self.assertEqual(vu["couleur2"],
                         configuration["profils"][deuxieme]["couleur"])

    def test_la_page_previent_quand_elle_n_a_rien_recu(self):
        """Macropad absent ou mode --simuler : il faut le DIRE.

        Une page vide et muette fait chercher le probleme au mauvais
        endroit ; c'est arrive."""
        vu = self._construire({"ordre": [], "profils": {}, "touches": 6,
                               "apps": {"repli": {"profil": "WINDOWS",
                                                  "abrege": "Win"},
                                        "liste": []},
                               "origine": "simulation"})
        self.assertTrue(vu["texte_vide"],
                        "aucun profil affiche, et rien pour l'expliquer")


class AncienFichierDeConfiguration(unittest.TestCase):
    """Un profils.json ecrit par la V1 doit encore se lire apres la mise a
    jour. Sinon, l'utilisateur perd ses macros en changeant de firmware :
    c'est exactement ce qu'on veut eviter."""

    def test_version_1_relue_comme_appui_court(self):
        import store
        ancien = {
            "version": 1,
            "ordre": ["CIVIL3D"],
            "profils": {"CIVIL3D": {"titre": "CIVIL 3D", "touches": [
                {"label": "MATCH", "type": "text_enter", "valeur": "_MATCHPROP"},
                {"label": "ANNUL", "type": "combo", "valeur": "CTRL+Z"},
                {"label": "", "type": "none", "valeur": ""},
            ]}},
        }
        profils, ordre, titres, couleurs, apps, repli = store.depuis_json(ancien, 6)
        touches = profils["CIVIL3D"]

        self.assertEqual(len(touches), 6)          # complete a six touches
        self.assertEqual(titres["CIVIL3D"], "CIVIL 3D")

        label, gestes = touches[0]
        self.assertEqual(label, "MATCH")
        self.assertEqual(gestes["court"], [("text_enter", "_MATCHPROP")])
        self.assertNotIn("long", gestes)           # les deux autres gestes
        self.assertNotIn("double", gestes)         # restent libres

        self.assertEqual(touches[1][1]["court"], [("combo", ("CTRL", "Z"))])
        self.assertEqual(touches[2][1], {})        # touche inactive

        # Et le tout reste tapable : rien de casse par la conversion.
        self.assertEqual(store.verifier(profils, ordre, 6), [])

    def test_version_2_non_touchee_par_la_conversion(self):
        # La conversion ne doit se declencher que sur les anciens fichiers.
        import store
        recent = {
            "version": 2,
            "ordre": ["WORD"],
            "profils": {"WORD": {"titre": "WORD", "touches": [
                {"label": "GRAS", "type": "ignore", "valeur": "ignore",
                 "court": {"type": "combo", "valeur": "CTRL+B"}},
            ]}},
        }
        profils, _, _, _, _, _ = store.depuis_json(recent, 6)
        self.assertEqual(profils["WORD"][0][1]["court"],
                         [("combo", ("CTRL", "B"))])


if __name__=='__main__': unittest.main(verbosity=2)
