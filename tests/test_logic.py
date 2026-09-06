"""Tests sur PC : temps, GPIO et transport simulés ; aucune validation USB physique."""
import sys, types, pathlib, unittest, time, runpy
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
            for _,actions in macros:
                self.assertTrue(compile_actions(actions,'FR_AZERTY'))
        for index in (0,1,3):
            seq=compile_actions(PROFILES['CIVIL3D'][index][1],'FR_AZERTY')
            self.assertEqual(seq[0],(37,)); self.assertEqual(seq[-1],(40,))
        self.assertEqual(compile_actions([('combo',('CTRL','Z'))],'FR_AZERTY'),[(-1,26)])
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
            Pin.levels[4]=0 if 2600 <= clock[0] < 2660 else 1
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
            for label, _ in macros:
                self.assertLessEqual(len(label), P.LABEL_MAX,
                                     "%s : '%s'" % (nom, label))

    def test_toutes_les_macros_usine_sont_tapables(self):
        import profiles as P
        for nom, macros in P.PROFILES.items():
            for label, actions in macros:
                compile_actions(actions, C.KEYBOARD_LAYOUT)

    def test_rotation_sur_six_touches(self):
        from profiles import ProfileManager
        import store
        profils, ordre, titres, origine = store.charger(6)
        self.assertEqual(origine, 'usine')
        p = ProfileManager(ordre, C.DEFAULT_PROFILE, profils, 6)
        self.assertEqual(len(p.macros), 6)
        self.assertEqual([p.move(1) for _ in range(4)],
                         ['WORD', 'WINDOWS', 'BLENDER', 'CIVIL3D'])

    # --- enregistrement JSON --------------------------------------------
    def test_aller_retour_json(self):
        import store
        profils, ordre = store.defauts()
        titres = {'CIVIL3D': 'CIVIL 3D'}
        ok, raison = store.enregistrer(profils, ordre, titres, 6)
        self.assertTrue(ok, raison)
        relus, ordre2, titres2, origine = store.charger(6)
        self.assertEqual(origine, 'fichier')
        self.assertEqual(ordre2, ordre)
        # Les macros relues doivent produire exactement les memes frappes.
        for nom in ordre:
            for i in range(6):
                self.assertEqual(
                    compile_actions(relus[nom][i][1], 'FR_AZERTY'),
                    compile_actions(profils[nom][i][1], 'FR_AZERTY'),
                    '%s B%d' % (nom, i + 1))

    def test_macro_intapable_refusee(self):
        import store
        profils, ordre = store.defauts()
        profils['CIVIL3D'][0] = ('KO', [('key', 'TOUCHE_QUI_NEXISTE_PAS')])
        ok, raison = store.enregistrer(profils, ordre, {}, 6)
        self.assertFalse(ok)
        self.assertIn('CIVIL3D', raison)

    def test_libelle_trop_long_refuse(self):
        import store
        profils, ordre = store.defauts()
        profils['WORD'][0] = ('BEAUCOUPTROPLONG', [('key', 'A')])
        ok, raison = store.enregistrer(profils, ordre, {}, 6)
        self.assertFalse(ok)

    def test_fichier_corrompu_repli_sur_usine(self):
        import store
        with open(C.PROFILES_FILE, 'w') as f:
            f.write('{ ceci n est pas du JSON')
        profils, ordre, titres, origine = store.charger(6)
        self.assertEqual(origine, 'usine')      # ne doit PAS planter
        self.assertEqual(len(profils['CIVIL3D']), 6)

    def test_fichier_incoherent_repli_sur_usine(self):
        import store, json as J
        # JSON valide, mais une macro impossible a taper.
        data = {'version': 1, 'ordre': ['X'], 'profils': {'X': {'titre': 'X',
                'touches': [{'label': 'A', 'type': 'key', 'valeur': 'INCONNU'}] * 6}}}
        with open(C.PROFILES_FILE, 'w') as f:
            J.dump(data, f)
        profils, ordre, titres, origine = store.charger(6)
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
        self.assertEqual(civil[0]["valeur"], "_MATCHPROP")
        self.assertEqual(civil[0]["type"], "text_enter")
        # Les combinaisons sont lisibles dans le formulaire.
        self.assertEqual(civil[2]["valeur"], "CTRL+Z")

    def test_enregistrement_valide(self):
        import json as J
        sortie = self._requete("GET", "/api/profils")
        data = J.loads(sortie.split(b"\r\n\r\n", 1)[1])
        data["profils"]["CIVIL3D"]["touches"][0] = {
            "label": "TALUS", "type": "text_enter", "valeur": "_GRADING"}
        reponse = self._requete("POST", "/api/profils",
                                J.dumps(data).encode())
        resultat = J.loads(reponse.split(b"\r\n\r\n", 1)[1])
        self.assertTrue(resultat["ok"], resultat.get("raison"))

        # La modification doit etre relue telle quelle par le firmware.
        import store
        profils, ordre, titres, origine = store.charger(6)
        self.assertEqual(origine, "fichier")
        self.assertEqual(profils["CIVIL3D"][0][0], "TALUS")
        frappes = compile_actions(profils["CIVIL3D"][0][1], "FR_AZERTY")
        self.assertEqual(len(frappes), len("_GRADING") + 1)   # + ENTREE
        self.assertEqual(frappes[0], (37,))                   # "_" en AZERTY

    def test_enregistrement_refuse_une_macro_intapable(self):
        import json as J
        sortie = self._requete("GET", "/api/profils")
        data = J.loads(sortie.split(b"\r\n\r\n", 1)[1])
        data["profils"]["WORD"]["touches"][0] = {
            "label": "KO", "type": "combo", "valeur": "CTRL+TOUCHE_BIDON"}
        reponse = self._requete("POST", "/api/profils", J.dumps(data).encode())
        resultat = J.loads(reponse.split(b"\r\n\r\n", 1)[1])
        self.assertFalse(resultat["ok"])
        self.assertIn("WORD", resultat["raison"])
        # Rien ne doit avoir ete ecrit : on reste sur les profils d'usine.
        import store
        self.assertEqual(store.charger(6)[3], "usine")

    def test_enregistrement_refuse_un_json_casse(self):
        import json as J
        reponse = self._requete("POST", "/api/profils", b"{pas du json")
        resultat = J.loads(reponse.split(b"\r\n\r\n", 1)[1])
        self.assertFalse(resultat["ok"])

    def test_retour_usine(self):
        import json as J, store
        profils, ordre = store.defauts()
        store.enregistrer(profils, ordre, {}, 6)
        self.assertEqual(store.charger(6)[3], "fichier")
        self._requete("POST", "/api/usine")
        self.assertEqual(store.charger(6)[3], "usine")

    def test_chemin_inconnu(self):
        self.assertIn(b"404", self._requete("GET", "/nimportequoi"))


if __name__=='__main__': unittest.main(verbosity=2)
