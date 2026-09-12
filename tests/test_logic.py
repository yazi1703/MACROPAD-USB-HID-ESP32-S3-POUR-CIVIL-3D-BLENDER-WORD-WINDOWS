"""Tests sur PC : temps, GPIO et transport simulés ; aucune validation USB physique."""
import ast, io, json, os, shutil, subprocess, sys, tempfile, types, pathlib, unittest, time, runpy
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
# framebuf existe sur la carte, pas sur un PC. Sans ce bouchon, sh1106.py
# ne s'importe pas ici et diag.controle() croirait a un firmware casse.
_fb = types.ModuleType('framebuf')
class _FrameBuffer:
    def __init__(self, *a, **kw): pass
    def fill(self, c): pass
    def text(self, *a, **kw): pass
    def pixel(self, x, y): return 0
_fb.FrameBuffer = _FrameBuffer; _fb.MONO_HLSB = 3; _fb.MONO_VLSB = 0
sys.modules['framebuf'] = _fb
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
        # B4, B5 et B6 de CIVIL3D ecrivent une commande _XXX suivie
        # d'Entree. B1 est le presse-papiers, B2 la touche modificatrice
        # et B3 la touche F3.
        for index in (3,4,5):
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
            # On se sert de B4 (GPIO7, _PLINE) : B1 est le presse-papiers
            # et son double appui retarde volontairement l'appui court, B2
            # est la touche modificatrice, B3 ne tape qu'une touche.
            # B4 est membre de combinaisons : cet appui de 60 ms traverse
            # donc le collecteur, qui doit le rendre intact.
            Pin.levels[7]=0 if 2600 <= clock[0] < 2660 else 1
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
        (profils, ordre, titres, couleurs, combos,
         apps, repli, origine) = store.charger(6)
        self.assertEqual(origine, 'usine')
        p = ProfileManager(ordre, C.DEFAULT_PROFILE, profils, 6)
        self.assertEqual(len(p.macros), 6)
        self.assertEqual([p.move(1) for _ in range(4)],
                         ['WORD', 'WINDOWS', 'BLENDER', 'CIVIL3D'])

    # --- enregistrement JSON --------------------------------------------
    def test_aller_retour_json(self):
        import store
        profils, ordre, titres, couleurs, combos, apps, repli = store.defauts()
        ok, raison = store.enregistrer(profils, ordre, titres, couleurs,
                                       combos, apps, repli, 6)
        self.assertTrue(ok, raison)
        (relus, ordre2, titres2, couleurs2, combos2,
         apps2, repli2, origine) = store.charger(6)
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
        profils, ordre, titres, couleurs, combos, apps, repli = store.defauts()
        profils['CIVIL3D'][0] = ('KO', {'court': [('key', 'TOUCHE_BIDON')]})
        ok, raison = store.enregistrer(profils, ordre, titres, couleurs,
                                       combos, apps, repli, 6)
        self.assertFalse(ok)
        self.assertIn('CIVIL3D', raison)

    def test_libelle_trop_long_refuse(self):
        import store
        profils, ordre, titres, couleurs, combos, apps, repli = store.defauts()
        profils['WORD'][0] = ('BEAUCOUPTROPLONG', {'court': [('key', 'A')]})
        ok, raison = store.enregistrer(profils, ordre, titres, couleurs,
                                       combos, apps, repli, 6)
        self.assertFalse(ok)

    def test_fichier_corrompu_repli_sur_usine(self):
        import store
        with open(C.PROFILES_FILE, 'w') as f:
            f.write('{ ceci n est pas du JSON')
        (profils, ordre, titres, couleurs, combos,
         apps, repli, origine) = store.charger(6)
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
        (profils, ordre, titres, couleurs, combos,
         apps, repli, origine) = store.charger(6)
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

        # L'affichage des combinaisons. Il ecrit en police doublee sur
        # deux lignes : c'est le dessin le plus haut de tout le firmware,
        # donc le plus expose au debordement vertical.
        essais = [(indices, label)
                  for liste in P.COMBOS.values()
                  for indices, label, _actions in liste]
        essais += [((0, 1), ''),                       # libelle vide
                   ((0, 1, 2, 3, 4, 5), 'X' * 16),     # les deux pires cas
                   ((0, 1), 'X' * 32)]                 # libelle trop long
        for indices, label in essais:
            from combos import nom_touches
            ecran.flash(nom_touches(indices), label, clock[0])
            for _ in range(C.COMBO_FLASH_MS + 20):
                ecran.tick(clock[0])
                clock[0] += 1
        # ... et l'ecran est bien revenu au tableau tout seul.
        self.assertIsNone(ecran.splash_until)

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
        # Chaque geste est une SUITE d'etapes, meme quand il n'y en a qu'une.
        self.assertEqual(civil[3]["court"][0]["valeur"], "_PLINE")
        self.assertEqual(civil[3]["court"][0]["type"], "text_enter")
        # Les combinaisons sont lisibles dans le formulaire.
        self.assertEqual(civil[0]["court"][0]["valeur"], "CTRL+C")
        self.assertEqual(civil[0]["double"][0]["valeur"], "CTRL+V")
        self.assertEqual(civil[0]["long"][0]["valeur"], "CTRL+Z")
        # L'appui long de B3 montre toute la vue.
        self.assertEqual(civil[2]["long"][0]["valeur"], "_ZOOM E")
        # Les combinaisons voyagent avec le profil, en numeros de touches
        # lisibles : [3, 4] c'est bien B3 et B4.
        combos = data["profils"]["CIVIL3D"]["combos"]
        self.assertEqual(combos[0]["touches"], [5, 6])
        self.assertEqual(combos[0]["label"], "VUE PREC.")
        self.assertEqual(combos[0]["actions"][0]["valeur"], "MPVIEWPREV")
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
        (profils, ordre, titres, couleurs, combos,
         apps, repli, origine) = store.charger(6)
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
        self.assertEqual(store.charger(6)[7], "usine")

    def test_enregistrement_refuse_un_json_casse(self):
        import json as J
        reponse = self._requete("POST", "/api/profils", b"{pas du json")
        resultat = J.loads(reponse.split(b"\r\n\r\n", 1)[1])
        self.assertFalse(resultat["ok"])

    def test_retour_usine(self):
        import store
        store.enregistrer(*store.defauts(), nb_touches=6)
        self.assertEqual(store.charger(6)[7], "fichier")
        self._requete("POST", "/api/usine")
        self.assertEqual(store.charger(6)[7], "usine")

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
            data["profils"]["CIVIL3D"]["touches"][3]["court"][0]["valeur"],
            "_PLINE")

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

        (profils, ordre, titres, couleurs, combos,
         apps, repli, origine) = store.charger(6)
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
        self.assertEqual(store.charger(6)[7], "usine")

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
        # B3 F3 a un appui long (la vue globale), pas de double.
        self.assertTrue(self.G.a_long[2])
        self.assertFalse(self.G.a_double[2])
        # B1 est le presse-papiers : les trois gestes sont occupes.
        self.assertTrue(self.G.a_long[0])
        self.assertTrue(self.G.a_double[0])
        # Et surtout : AUCUNE des touches de commande n'a de double appui.
        # C'est ce qui les garde instantanees - un double appui, c'est
        # GESTE_DOUBLE_MS d'attente avant de savoir quoi envoyer.
        for index in (2, 3, 4, 5):
            self.assertFalse(self.G.a_double[index], "B%d" % (index + 1))
        # B2 est la touche modificatrice : mode a part.
        self.assertTrue(self.G.a_maintien[1])
        self.assertTrue(self.G.a_maintien2[1])
        self.assertFalse(self.G.a_maintien[0])


class CombinaisonsSimultanees(unittest.TestCase):
    """Deux touches ensemble = une macro a elles.

    Le point qui a decide de toute la conception : ne pas ralentir les
    appuis simples. On le verifie ici touche par touche, et jusque dans
    l'horodatage transmis a la machine a gestes.
    """

    def setUp(self):
        clock[0] = 0
        from combos import Combos, APPUI, RELACHEMENT, nom_touches
        self.APPUI, self.RELACHEMENT = APPUI, RELACHEMENT
        self.nom_touches = nom_touches
        self.C = Combos(6, fenetre_ms=50)
        self.C.configurer([
            ((2, 3), "VUE PREV", [("text_enter", "MPVIEWPREV")]),
            ((4, 5), "VUE SUIV", [("text_enter", "MPVIEWNEXT")]),
        ])

    # --- ce qui ne doit RIEN couter --------------------------------------
    def test_une_touche_hors_combinaison_passe_sans_delai(self):
        # B1 (index 0) n'entre dans aucune combinaison.
        self.assertFalse(self.C.membres[0])
        combo, differes = self.C.appui(0, 100)
        self.assertIsNone(combo)
        self.assertEqual(differes, [(self.APPUI, 0, 100)])
        combo, differes = self.C.relachement(0, 160)
        self.assertEqual(differes, [(self.RELACHEMENT, 0, 160)])

    def test_une_tape_rapide_sur_une_membre_ne_perd_rien(self):
        # Appui puis relachement AVANT la fin de la fenetre : on libere
        # tout au relachement, donc aucune latence ajoutee.
        combo, differes = self.C.appui(2, 100)
        self.assertIsNone(combo)
        self.assertEqual(differes, [])              # retenu un instant

        combo, differes = self.C.relachement(2, 130)
        self.assertIsNone(combo)
        self.assertEqual(differes, [(self.APPUI, 2, 100),
                                    (self.RELACHEMENT, 2, 130)])

    def test_l_horodatage_d_origine_est_preserve(self):
        # Touche membre gardee enfoncee : l'appui n'est transmis qu'a la
        # fin de la fenetre, mais avec l'instant du VRAI appui. Sans
        # cela, tout appui long partirait en retard.
        self.C.appui(2, 100)
        combo, differes = self.C.service(120)        # fenetre encore ouverte
        self.assertEqual(differes, [])
        combo, differes = self.C.service(150)        # fenetre fermee
        self.assertIsNone(combo)
        self.assertEqual(differes, [(self.APPUI, 2, 100)])

    # --- la reconnaissance -------------------------------------------------
    def test_deux_touches_ensemble_declenchent_la_combinaison(self):
        self.C.appui(2, 100)
        combo, differes = self.C.appui(3, 120)
        self.assertIsNotNone(combo)
        cle, libelle, actions = combo
        self.assertEqual(cle, (2, 3))
        self.assertEqual(libelle, "VUE PREV")
        self.assertEqual(actions, [("text_enter", "MPVIEWPREV")])
        # ET SURTOUT : aucun appui simple n'est parti.
        self.assertEqual(differes, [])

    def test_l_ordre_des_doigts_n_a_pas_d_importance(self):
        self.C.appui(3, 100)
        combo, _ = self.C.appui(2, 115)
        self.assertEqual(combo[0], (2, 3))

    def test_deux_appuis_trop_espaces_restent_deux_appuis(self):
        self.C.appui(2, 100)
        combo, differes = self.C.appui(3, 400)       # bien hors fenetre
        self.assertIsNone(combo)
        # Le premier appui est libere, le second ouvre sa propre fenetre.
        self.assertEqual(differes, [(self.APPUI, 2, 100)])
        combo, differes = self.C.service(460)
        self.assertEqual(differes, [(self.APPUI, 3, 400)])

    def test_les_relachements_de_la_combinaison_sont_avales(self):
        self.C.appui(2, 100)
        self.C.appui(3, 120)
        combo, differes = self.C.relachement(2, 300)
        self.assertEqual(differes, [])
        combo, differes = self.C.relachement(3, 320)
        self.assertEqual(differes, [])
        # Et on est bien revenu au repos : une nouvelle paire fonctionne.
        self.C.appui(2, 400)
        combo, _ = self.C.appui(3, 420)
        self.assertIsNotNone(combo)

    def test_rouler_les_doigts_ne_declenche_pas_une_seconde_fois(self):
        self.C.appui(4, 100)
        combo, _ = self.C.appui(5, 115)
        self.assertIsNotNone(combo)
        # On garde B5 et B6 enfoncees, et on pose un doigt sur B3.
        combo, differes = self.C.appui(2, 200)
        self.assertIsNone(combo)
        self.assertEqual(differes, [], "un appui parasite a ete transmis")
        combo, differes = self.C.relachement(2, 260)
        self.assertEqual(differes, [])

    # --- annulations -------------------------------------------------------
    def test_esc_abandonne_une_combinaison_en_attente(self):
        self.C.appui(2, 100)
        self.C.reinitialiser()                       # ce que fait ESC
        combo, differes = self.C.service(200)
        self.assertIsNone(combo)
        self.assertEqual(differes, [], "un appui retenu est parti apres ESC")

    def test_apres_esc_le_relachement_ne_reveille_rien(self):
        self.C.appui(2, 100)
        self.C.reinitialiser()
        combo, differes = self.C.relachement(2, 200)
        self.assertIsNone(combo)
        # Le relachement est transmis, mais la machine a gestes l'ignore
        # puisque l'appui n'a jamais eu lieu de son point de vue.
        self.assertEqual(differes, [(self.RELACHEMENT, 2, 200)])

    # --- extension a trois touches -----------------------------------------
    def test_une_paire_attend_si_un_trio_peut_encore_se_former(self):
        self.C.configurer([
            ((2, 3), "PAIRE", [("key", "F5")]),
            ((2, 3, 4), "TRIO", [("key", "F6")]),
        ])
        self.C.appui(2, 100)
        combo, _ = self.C.appui(3, 115)
        self.assertIsNone(combo, "la paire a declenche alors qu'un trio "
                                 "pouvait encore se former")
        # La troisieme arrive : c'est le trio.
        combo, _ = self.C.appui(4, 130)
        self.assertEqual(combo[1], "TRIO")

    def test_le_trio_ne_venant_pas_la_paire_part_a_la_fin_de_la_fenetre(self):
        self.C.configurer([
            ((2, 3), "PAIRE", [("key", "F5")]),
            ((2, 3, 4), "TRIO", [("key", "F6")]),
        ])
        self.C.appui(2, 100)
        self.C.appui(3, 115)
        combo, differes = self.C.service(160)
        self.assertEqual(combo[1], "PAIRE")
        self.assertEqual(differes, [])

    def test_une_paire_sans_trio_declenche_sans_attendre(self):
        # Aucune combinaison plus grande ne partage ces touches : inutile
        # d'attendre la fin de la fenetre.
        self.C.appui(2, 100)
        combo, _ = self.C.appui(3, 101)
        self.assertIsNotNone(combo)

    def test_une_combinaison_d_une_seule_touche_est_ignoree(self):
        self.C.configurer([((2,), "ABSURDE", [("key", "F5")])])
        self.assertFalse(self.C.membres[2],
                         "une touche seule ne doit pas devenir une "
                         "combinaison : elle deviendrait inutilisable")

    def test_nom_pour_l_ecran(self):
        self.assertEqual(self.nom_touches((2, 3)), "B3+B4")
        self.assertEqual(self.nom_touches((0, 2, 5)), "B1+B3+B6")

    # --- l'integration avec la machine a gestes ---------------------------
    def test_l_appui_long_d_une_touche_membre_part_a_l_heure(self):
        """LE test qui compte : une touche membre d'une combinaison ne
        doit pas voir son appui long decale par la fenetre."""
        from gestures import Gestes, LONG
        gestes = Gestes(6, long_ms=400, double_ms=200)
        gestes.configurer([
            ("", {}), ("", {}),
            ("ZOOM", {"court": [("key", "F3")], "long": [("key", "F5")]}),
            ("", {}), ("", {}), ("", {}),
        ])

        def transmettre(differes):
            sortis = []
            for front, index, instant in differes:
                geste = (gestes.appui(index, instant) if front == self.APPUI
                         else gestes.relachement(index, instant))
                if geste:
                    sortis.append((index, geste))
            return sortis

        # Appui a t=100, garde enfonce. La fenetre se ferme a 150.
        transmettre(self.C.appui(2, 100)[1])
        transmettre(self.C.service(120)[1])
        transmettre(self.C.service(150)[1])          # l'appui est transmis

        # A t=499, l'appui long ne doit pas encore etre parti...
        self.assertEqual(gestes.service(499), [])
        # ...et a t=500, soit 400 ms apres le VRAI appui, il part.
        self.assertEqual(gestes.service(500), [(2, LONG)])


class CombinaisonsDansLaBoucleReelle(unittest.TestCase):
    """Le collecteur branche sur main.py, du GPIO jusqu'aux octets USB.

    Les tests precedents verifient le collecteur seul. Ceux-ci font
    tourner la VRAIE boucle de main.py, avec de vrais rebonds de contact
    et de vrais paquets clavier : c'est le seul endroit ou un cablage
    oublie se voit.
    """

    def setUp(self):
        clock[0] = 0
        Pin.levels = {}
        try:
            os.remove(C.PROFILES_FILE)
        except OSError:
            pass

    tearDown = setUp

    def _boucle(self, chronologie, fin=3200):
        """Fait tourner main.run() en pilotant les GPIO a chaque ms."""
        import main, runtime
        transport = Transport()

        def sleep_simule(ms):
            clock[0] += ms
            chronologie(clock[0])
            if clock[0] >= fin:
                raise KeyboardInterrupt()

        with patch.object(runtime, 'interface', transport), \
             patch.object(runtime, 'safe_mode', False), \
             patch.object(runtime, 'config_mode', False), \
             patch.object(main, 'sleep_ms', sleep_simule):
            with self.assertRaises(KeyboardInterrupt):
                main.run()
        return [rapport for rapport in transport.sent if rapport]

    @staticmethod
    def _attendu(actions):
        return compile_actions(actions, C.KEYBOARD_LAYOUT)

    def test_deux_touches_ensemble_tapent_la_commande_de_la_combinaison(self):
        """B3+B4 tape MPVIEWNEXT, et surtout PAS F3 ni _PLINE."""
        def chrono(t):
            # Doigts poses a 12 ms d'intervalle : personne n'appuie deux
            # touches a la milliseconde pres.
            Pin.levels[6] = 0 if 2600 <= t < 2700 else 1     # B3
            Pin.levels[7] = 0 if 2612 <= t < 2700 else 1     # B4

        rapports = self._boucle(chrono)
        attendu = self._attendu([("text_enter", "MPVIEWNEXT")])
        self.assertEqual(rapports, attendu)
        # Les macros des deux touches seules ne sont jamais parties.
        self.assertNotIn(self._attendu([("key", "F3")])[0], rapports)
        self.assertNotIn(self._attendu([("text_enter", "_PLINE")])[0], rapports)

    def test_une_touche_membre_seule_garde_sa_macro(self):
        """Le collecteur rend l'appui intact : B3 seule tape toujours F3."""
        def chrono(t):
            Pin.levels[6] = 0 if 2600 <= t < 2700 else 1

        rapports = self._boucle(chrono)
        self.assertEqual(rapports, self._attendu([("key", "F3")]))

    def test_un_appui_long_sur_une_touche_membre_part_a_l_heure(self):
        """Le vrai enjeu de l'horodatage d'origine, mesure de bout en bout.

        Sans lui, l'appui long partirait avec le retard de la fenetre.
        """
        import main, runtime
        transport = Transport()
        instants = []

        def sleep_simule(ms):
            clock[0] += ms
            Pin.levels[6] = 0 if 2600 <= clock[0] < 3400 else 1
            # Le PREMIER rapport non vide : le tout premier tick() du
            # clavier envoie un rapport vide, il ne compte pas.
            if not instants and [r for r in transport.sent if r]:
                instants.append(clock[0])
            if clock[0] >= 3600:
                raise KeyboardInterrupt()

        with patch.object(runtime, 'interface', transport), \
             patch.object(runtime, 'safe_mode', False), \
             patch.object(runtime, 'config_mode', False), \
             patch.object(main, 'sleep_ms', sleep_simule):
            with self.assertRaises(KeyboardInterrupt):
                main.run()

        rapports = [rapport for rapport in transport.sent if rapport]
        self.assertEqual(rapports, self._attendu([("text_enter", "_ZOOM E")]))
        # L'appui est DETECTE apres le filtre anti-rebond, et la macro
        # longue part GESTE_LONG_MS plus tard - PAS une fenetre de
        # combinaison de plus. C'est tout l'interet de l'horodatage
        # d'origine, et cet ecart de 50 ms se sentirait sous le doigt.
        theorique = 2600 + C.DEBOUNCE_MS + C.GESTE_LONG_MS
        self.assertGreaterEqual(instants[0], theorique)
        self.assertLess(instants[0] - theorique, 4 * C.LOOP_MS,
                        "parti a %d au lieu de %d" % (instants[0], theorique))

    def test_esc_annule_une_combinaison_en_cours_de_formation(self):
        """Exigence explicite : ESC ne declenche jamais rien d'autre."""
        def chrono(t):
            Pin.levels[6] = 0 if 2600 <= t < 2900 else 1     # B3 maintenue
            # ESC pendant la fenetre, donc avant que le sort de B3 soit fixe.
            Pin.levels[14] = 0 if 2630 <= t < 2690 else 1

        rapports = self._boucle(chrono)
        # ESC est parti, et rien d'autre : ni F3, ni la vue globale de
        # l'appui long, alors que B3 est restee enfoncee 300 ms.
        self.assertEqual(rapports, self._attendu([("key", "ESC")]))


class CombinaisonsDansLaConfiguration(unittest.TestCase):
    """Les combinaisons voyagent dans profils.json comme le reste.

    Meme exigence que pour les macros : rien n'est enregistre sans avoir
    ete verifie, et un fichier ecrit AVANT les combinaisons doit continuer
    de se relire sans rien perdre.
    """

    def setUp(self):
        try:
            os.remove(C.PROFILES_FILE)
        except OSError:
            pass

    tearDown = setUp

    # --- les valeurs d'usine -------------------------------------------
    def test_les_combinaisons_d_usine_sont_chargees(self):
        import store, profiles as P
        combos = store.defauts()[4]
        self.assertEqual(combos["CIVIL3D"], list(P.COMBOS["CIVIL3D"]))
        # Un profil sans combinaison n'en invente pas.
        self.assertEqual(combos.get("WORD", []), [])

    def test_les_valeurs_d_usine_sont_saines(self):
        import store, profiles as P
        profils = store.defauts()[0]
        self.assertEqual(
            store.verifier_combos(P.COMBOS, profils, 6), [])

    def test_aucune_combinaison_ne_touche_la_modificatrice(self):
        """B2 tient Maj ou Ctrl enfoncee : la prendre dans une combinaison
        la rendrait inutilisable pour ce a quoi elle sert."""
        import profiles as P
        for nom, liste in P.COMBOS.items():
            for indices, label, _actions in liste:
                self.assertNotIn(0, indices, "%s %s" % (nom, label))
                self.assertNotIn(1, indices, "%s %s" % (nom, label))

    # --- aller-retour vers le fichier ----------------------------------
    def test_aller_retour_par_le_fichier(self):
        import store
        profils, ordre, titres, couleurs, combos, apps, repli = store.defauts()
        ok, raison = store.enregistrer(profils, ordre, titres, couleurs,
                                       combos, apps, repli, 6)
        self.assertTrue(ok, raison)
        relus = store.charger(6)[4]
        self.assertEqual(relus["CIVIL3D"], combos["CIVIL3D"])
        self.assertEqual(store.charger(6)[7], "fichier")

    def test_les_numeros_du_fichier_sont_ceux_du_pad(self):
        """Dans le JSON, [3, 4] c'est B3 et B4 - pas les indices internes."""
        import store
        data = store.vers_json(6)
        combos = data["profils"]["CIVIL3D"]["combos"]
        premiere = combos[0]
        self.assertEqual(premiere["touches"], [5, 6])
        # ... et en interne, ces memes touches portent 4 et 5.
        interne = store.combos_depuis_json(combos)
        self.assertEqual(interne[0][0], (4, 5))

    def test_le_libelle_est_tronque_pas_refuse(self):
        import store
        interne = store.combos_depuis_json(
            [{"touches": [3, 4], "label": "X" * 40, "actions": []}])
        self.assertEqual(len(interne[0][1]), 16)

    # --- migration d'un fichier ecrit avant les combinaisons -------------
    def _fichier_sans_combos(self):
        import store, json as J
        data = store.vers_json(6)
        for bloc in data["profils"].values():
            bloc.pop("combos")
        data.pop("origine", None)
        with open(C.PROFILES_FILE, "w") as fichier:
            J.dump(data, fichier)

    def test_un_fichier_sans_combos_recupere_celles_d_usine(self):
        import store, profiles as P
        self._fichier_sans_combos()
        profils, ordre, titres, couleurs, combos, apps, repli, origine = \
            store.charger(6)
        self.assertEqual(origine, "fichier")     # le reste est bien relu
        self.assertEqual(combos["CIVIL3D"], list(P.COMBOS["CIVIL3D"]))

    def test_une_liste_vide_est_respectee(self):
        """"Je n'en veux aucune" doit survivre au redemarrage."""
        import store, json as J
        data = store.vers_json(6)
        data["profils"]["CIVIL3D"]["combos"] = []
        data.pop("origine", None)
        with open(C.PROFILES_FILE, "w") as fichier:
            J.dump(data, fichier)
        self.assertEqual(store.charger(6)[4]["CIVIL3D"], [])

    # --- ce qui doit etre refuse ----------------------------------------
    def _refuse(self, combos, morceau):
        import store
        profils = store.defauts()[0]
        problemes = store.verifier_combos(combos, profils, 6)
        self.assertTrue(problemes, "aucun probleme signale")
        self.assertIn(morceau, " ; ".join(problemes))

    def test_une_seule_touche_n_est_pas_une_combinaison(self):
        self._refuse({"CIVIL3D": [((2,), "SEULE", [("key", "F3")])]},
                     "au moins deux touches")

    def test_une_touche_qui_n_existe_pas(self):
        self._refuse({"CIVIL3D": [((2, 9), "TROP", [("key", "F3")])]},
                     "B10 n'existe pas")

    def test_la_meme_touche_deux_fois(self):
        self._refuse({"CIVIL3D": [((2, 2), "DOUBLE", [("key", "F3")])]},
                     "deux fois")

    def test_deux_combinaisons_sur_les_memes_touches(self):
        self._refuse({"CIVIL3D": [((2, 3), "UNE", [("key", "F3")]),
                                  ((3, 2), "AUTRE", [("key", "F4")])]},
                     "deja prise")

    def test_un_maintien_est_impossible(self):
        # Un maintien se relache quand SA touche se relache. Une
        # combinaison n'en a pas une seule a surveiller : Ctrl resterait
        # enfonce cote Windows, et plus rien ne repondrait normalement.
        self._refuse({"CIVIL3D": [((2, 3), "CTRL",
                                   [("maintien", ("CTRL",))])]},
                     "resterait enfoncee")

    def test_une_macro_intapable_est_refusee(self):
        self._refuse({"CIVIL3D": [((2, 3), "EURO", [("text", "100 EUR \u20ac")])]},
                     "B3+B4")

    # --- ce que la MAIN interdit ----------------------------------------
    def test_deux_touches_du_meme_doigt_sont_refusees(self):
        """B2 et B3 sont toutes les deux sous l'index : injouable.

        Ce controle est le seul qui parle du monde physique. Sans lui, la
        combinaison serait MUETTE - elle enverrait les deux macros l'une
        apres l'autre - et rien n'expliquerait pourquoi.
        """
        self._refuse({"CIVIL3D": [((1, 2), "INDEX", [("key", "F3")])]},
                     "meme doigt")

    def test_le_message_nomme_les_touches_et_le_doigt(self):
        import store
        profils = store.defauts()[0]
        problemes = store.verifier_combos(
            {"CIVIL3D": [((1, 2), "X", [("key", "F3")])]}, profils, 6)
        self.assertIn("B2 et B3", problemes[0])
        self.assertIn("index", problemes[0])

    def test_les_combinaisons_d_usine_sont_toutes_jouables(self):
        """Aucune paire d'usine ne tombe sous un seul doigt."""
        import store, profiles as P, config as C
        doigts = C.DOIGTS
        for nom, liste in P.COMBOS.items():
            for indices, label, _actions in liste:
                portes = [doigts[i] for i in indices]
                self.assertEqual(len(set(portes)), len(portes),
                                 "%s %s : %s" % (nom, label, portes))

    def test_sans_table_de_doigts_rien_n_est_verifie(self):
        """Un pad remonte autrement met DOIGTS a None : plus de controle."""
        import store, config as C
        ancien = C.DOIGTS
        C.DOIGTS = None
        try:
            profils = store.defauts()[0]
            self.assertEqual(
                store.verifier_combos(
                    {"CIVIL3D": [((1, 2), "X", [("key", "F3")])]}, profils, 6),
                [])
        finally:
            C.DOIGTS = ancien

    def test_un_profil_inconnu(self):
        self._refuse({"INEXISTANT": [((2, 3), "X", [("key", "F3")])]},
                     "n'existe pas")

    def test_verifier_refuse_l_enregistrement(self):
        """Le controle est bien branche sur le chemin d'enregistrement."""
        import store
        profils, ordre, titres, couleurs, combos, apps, repli = store.defauts()
        combos["CIVIL3D"] = [((2,), "SEULE", [("key", "F3")])]
        ok, raison = store.enregistrer(profils, ordre, titres, couleurs,
                                       combos, apps, repli, 6)
        self.assertFalse(ok)
        self.assertIn("au moins deux touches", raison)
        # Et rien n'a ete ecrit : la configuration precedente est intacte.
        self.assertFalse(os.path.exists(C.PROFILES_FILE))

    def test_un_fichier_combos_illisible_retombe_sur_l_usine(self):
        import store, json as J, profiles as P
        data = store.vers_json(6)
        data["profils"]["CIVIL3D"]["combos"] = "n'importe quoi"
        data.pop("origine", None)
        with open(C.PROFILES_FILE, "w") as fichier:
            J.dump(data, fichier)
        profils, ordre, titres, couleurs, combos, apps, repli, origine = \
            store.charger(6)
        self.assertEqual(origine, "usine")
        self.assertEqual(combos["CIVIL3D"], list(P.COMBOS["CIVIL3D"]))


class SuitesDEtapesEtPauses(unittest.TestCase):
    """Un geste peut enchainer plusieurs frappes, avec des pauses.

    Le cas qui a motive tout ca : taper _PURGE, attendre que la boite de
    dialogue s'ouvre, puis Ctrl+S. Sans pause, le Ctrl+S part dans le
    vide. Avec une pause BLOQUANTE, le macropad se figerait - c'est
    justement ce que l'architecture interdit.
    """

    def setUp(self):
        clock[0] = 0
        try:
            import os
            os.remove(C.PROFILES_FILE)
        except OSError:
            pass

    tearDown = setUp

    # --- la traduction --------------------------------------------------
    def test_la_pause_se_compile_en_marqueur(self):
        from layouts import compile_actions, PAUSE
        suite = compile_actions([("text", "a"), ("pause", "300"),
                                 ("key", "F5")], "FR_AZERTY")
        self.assertEqual(len(suite), 3)
        self.assertEqual(suite[1], (PAUSE, 300))
        self.assertEqual(suite[2], (62,))          # F5

    def test_une_pause_aberrante_est_refusee_avant_la_premiere_frappe(self):
        from layouts import compile_actions
        for mauvaise in ("abc", "-10", str(C.PAUSE_MAX_MS + 1)):
            with self.assertRaises(ValueError, msg=mauvaise):
                compile_actions([("pause", mauvaise)], "FR_AZERTY")

    # --- le deroulement ---------------------------------------------------
    def test_la_pause_retarde_la_suite_sans_bloquer(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.submit([("key", "TAB"), ("pause", "300"), ("key", "F5")])

        # Avant la pause : la premiere touche est partie.
        pump(k, 0, 100)
        self.assertIn((43,), t.sent)               # TAB
        self.assertNotIn((62,), t.sent)            # F5 pas encore

        # Pendant la pause, la machine tourne : tick() rend la main a
        # chaque fois, ce qui laisse la boucle lire les touches et animer
        # l'ecran. Rien n'est envoye pour autant.
        avant = len(t.sent)
        pump(k, 100, 150)
        self.assertEqual(len(t.sent), avant, "des frappes pendant la pause")
        self.assertFalse(k.fault, "le garde-fou s'est declenche")

        # Apres la pause : la suite part.
        pump(k, 250, 200)
        self.assertIn((62,), t.sent)               # F5

    def test_une_longue_pause_ne_declenche_pas_le_garde_fou(self):
        # Le garde-fou coupe au bout de HID_TIMEOUT_MS sans progres. Une
        # pause EST un progres : sans cette distinction, toute macro
        # contenant une pause d'une seconde serait coupee.
        self.assertGreater(C.PAUSE_MAX_MS, C.HID_TIMEOUT_MS)
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.submit([("key", "TAB"), ("pause", "3000"), ("key", "F5")])
        pump(k, 0, 3400)
        self.assertFalse(k.fault, "le garde-fou a coupe pendant la pause")
        self.assertIn((62,), t.sent)

    def test_esc_interrompt_une_macro_en_pleine_pause(self):
        t = Transport(); k = HIDKeyboard(t); k.tick(0)
        k.submit([("key", "TAB"), ("pause", "3000"), ("key", "F5")])
        pump(k, 0, 100)
        k.escape(100)
        pump(k, 102, 300)
        self.assertIn((41,), t.sent)               # Echap est parti
        self.assertNotIn((62,), t.sent)            # la suite est abandonnee
        self.assertEqual(t.sent[-1], ())

    # --- l'aller-retour par la page web -----------------------------------
    def test_une_suite_survit_a_l_enregistrement(self):
        import store
        data = store.vers_json(6)
        data["profils"]["CIVIL3D"]["touches"][5]["double"] = [
            {"type": "text_enter", "valeur": "_PURGE"},
            {"type": "pause", "valeur": "500"},
            {"type": "combo", "valeur": "CTRL+S"},
        ]
        ok, raison = store.enregistrer_json(data, 6)
        self.assertTrue(ok, raison)

        profils = store.charger(6)[0]
        self.assertEqual(profils["CIVIL3D"][5][1]["double"],
                         [("text_enter", "_PURGE"), ("pause", "500"),
                          ("combo", ("CTRL", "S"))])
        # Et la page la relit telle quelle.
        relu = store.vers_json(6)["profils"]["CIVIL3D"]["touches"][5]["double"]
        self.assertEqual(len(relu), 3)
        self.assertEqual(relu[1], {"type": "pause", "valeur": "500"})

    def test_une_pause_trop_longue_est_refusee_a_l_enregistrement(self):
        import store
        data = store.vers_json(6)
        data["profils"]["WORD"]["touches"][0]["court"] = [
            {"type": "pause", "valeur": str(C.PAUSE_MAX_MS + 1000)}]
        ok, raison = store.enregistrer_json(data, 6)
        self.assertFalse(ok)
        self.assertIn("WORD", raison)

    def test_l_ancienne_forme_a_une_seule_action_se_relit(self):
        # Un profils.json ecrit avant les suites range UN objet par geste.
        import store
        (profils, ordre, titres, couleurs, combos,
         apps, repli) = store.depuis_json({
            "version": 2, "ordre": ["X"],
            "profils": {"X": {"titre": "X", "touches": [
                {"label": "A", "court": {"type": "combo", "valeur": "CTRL+S"}},
            ]}},
        }, 6)
        self.assertEqual(profils["X"][0][1]["court"],
                         [("combo", ("CTRL", "S"))])


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
        self.assertEqual(label, "MAJ")
        # Maj d'abord : c'est le maintien INSTANTANE, et celui qu'on
        # utilise le plus, main droite a la souris.
        self.assertEqual(gestes["court"], [("maintien", ("SHIFT",))])
        self.assertEqual(gestes["double"], [("maintien", ("CTRL",))])
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
        _, _, _, couleurs, _, _, _ = store.defauts()
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

        _, _, _, couleurs, _, _, _, origine = store.charger(6)
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
        _, _, _, couleurs, _, _, _, _ = store.charger(6)
        self.assertEqual(couleurs["CIVIL3D"], tuple(C.RGB_COULEURS["CIVIL3D"]))


class ControleGeneral(unittest.TestCase):
    """« Rien ne marche » : une seule commande doit dire par ou commencer.

    Ces tests naissent d'un cas reel, et d'un defaut que j'avais
    introduit : le firmware neuf lisait C.GESTE_COMBO_MS en direct, alors
    que le projet dit de GARDER son config.py en televersant. Resultat,
    main.py plantait au demarrage - et une seule ligne manquante donnait
    TROIS pannes simultanees : pas de clavier, pas de LED, pas de liaison
    avec le PC. On cherche une soudure pendant une heure.
    """

    def test_un_config_ancien_ne_doit_plus_empecher_le_demarrage(self):
        """Le test qui compte : main.run() demarre sans les reglages neufs."""
        import main
        manquants = ("GESTE_COMBO_MS", "COMBO_FLASH_MS", "DOIGTS")
        gardes = {}
        for nom in manquants:
            gardes[nom] = getattr(C, nom)
            delattr(C, nom)
        main._manquants[:] = []
        transport = Transport()

        def sleep_simule(ms):
            clock[0] += ms
            if clock[0] >= 400:
                raise KeyboardInterrupt()

        try:
            import runtime
            with patch.object(runtime, 'interface', transport), \
                 patch.object(runtime, 'safe_mode', False), \
                 patch.object(runtime, 'config_mode', False), \
                 patch.object(main, 'sleep_ms', sleep_simule):
                with self.assertRaises(KeyboardInterrupt):
                    main.run()
        finally:
            for nom, valeur in gardes.items():
                setattr(C, nom, valeur)

        # Il a demarre, ET il a dit ce qui manquait plutot que de se taire.
        self.assertIn("GESTE_COMBO_MS", main._manquants)

    def test_une_panne_de_demarrage_est_affichee_pas_avalee(self):
        """Un firmware qui plante ne doit pas donner un pad muet.

        Sans filet : ecran fige, LED eteintes, aucune touche, et le
        compagnon qui dit "macropad non connecte". Trois symptomes, zero
        indice. L'ecran doit nommer le coupable.
        """
        import main
        affiche = []

        class EcranEspion:
            def __init__(self):
                affiche.append(self)
                self.lignes = []

            def message(self, *lignes):
                self.lignes = [str(l) for l in lignes]

            def flush_startup(self):
                pass

        def exploser():
            raise ValueError("config.py incomplet")

        sortie = io.StringIO()
        with patch.object(main, 'run', exploser), \
             patch('display.Display', EcranEspion), \
             patch('sys.stdout', sortie):
            with self.assertRaises(ValueError):
                main.demarrer()

        texte = sortie.getvalue()
        self.assertIn("N'A PAS PU DEMARRER", texte)
        self.assertIn("diag.controle()", texte)
        # Et l'ecran, lui aussi, dit quelque chose.
        self.assertTrue(affiche, "aucun ecran n'a ete sollicite")
        lignes = " ".join(affiche[0].lignes)
        self.assertIn("PANNE", lignes)
        self.assertIn("config.py", lignes)
        self.assertIn("diag.controle()", lignes)

    def test_un_ecran_absent_n_aggrave_pas_la_panne(self):
        """Le filet ne doit jamais masquer l'erreur d'origine."""
        import main

        def exploser():
            raise ValueError("la vraie cause")

        def pas_d_ecran(*a, **kw):
            raise OSError("pas d'ecran")

        with patch.object(main, 'run', exploser), \
             patch('display.Display', pas_d_ecran), \
             patch('sys.stdout', io.StringIO()):
            with self.assertRaises(ValueError) as capture:
                main.demarrer()
        self.assertIn("la vraie cause", str(capture.exception))

    def test_un_ctrl_c_n_est_pas_une_panne(self):
        import main

        def arreter():
            raise KeyboardInterrupt()

        sortie = io.StringIO()
        with patch.object(main, 'run', arreter), patch('sys.stdout', sortie):
            with self.assertRaises(KeyboardInterrupt):
                main.demarrer()
        self.assertNotIn("N'A PAS PU DEMARRER", sortie.getvalue())

    def test_le_repli_vaut_la_valeur_du_depot(self):
        """Un repli qui differerait du depot ferait un pad au comportement
        different selon l'age du config.py : piege absolu."""
        import main
        for nom, defaut in main.REGLAGES_NEUFS:
            self.assertEqual(getattr(C, nom), defaut,
                             "%s : le repli de main.py a diverge de config.py"
                             % nom)

    def test_reglage_prefere_toujours_config(self):
        import main
        self.assertEqual(main.reglage("GESTE_COMBO_MS", 999), C.GESTE_COMBO_MS)
        self.assertEqual(main.reglage("CONSTANTE_QUI_N_EXISTE_PAS", 7), 7)

    # --- diag.controle() -------------------------------------------------
    def _controle(self):
        import diag
        sortie = io.StringIO()
        with patch('sys.stdout', sortie):
            ok = diag.controle()
        return ok, sortie.getvalue()

    def test_controle_signale_un_reglage_manquant(self):
        garde = C.GESTE_COMBO_MS
        del C.GESTE_COMBO_MS
        try:
            ok, texte = self._controle()
        finally:
            C.GESTE_COMBO_MS = garde
        self.assertFalse(ok)
        self.assertIn("config.GESTE_COMBO_MS", texte)
        self.assertIn("plus ancien que le firmware", texte)

    def test_controle_signale_les_interrupteurs_a_False(self):
        """C'est LA cause de « les LED ne s'allument pas »."""
        garde = C.RGB_ENABLED
        C.RGB_ENABLED = False
        try:
            ok, texte = self._controle()
        finally:
            C.RGB_ENABLED = garde
        self.assertFalse(ok)
        self.assertIn("RGB_ENABLED", texte)
        self.assertIn("eteintes", texte)

    def test_controle_signale_le_safe_mode(self):
        """En SAFE MODE il n'y a ni clavier ni liaison : deux pannes, une cause."""
        import runtime
        with patch.object(runtime, 'safe_mode', True):
            ok, texte = self._controle()
        self.assertFalse(ok)
        self.assertIn("SAFE MODE", texte)
        self.assertIn("ni clavier", texte)

    def test_controle_signale_une_broche_reservee(self):
        anciennes = C.BUTTON_PINS
        C.BUTTON_PINS = (4, 5, 6, 30, 12, 13)      # GPIO30 = flash SPICLK
        try:
            ok, texte = self._controle()
        finally:
            C.BUTTON_PINS = anciennes
        self.assertFalse(ok)
        self.assertIn("GPIO30", texte)

    def test_controle_distingue_un_fichier_absent_d_un_fichier_casse(self):
        import diag
        garde = dict(sys.modules)
        sys.modules['combos'] = None               # provoque l'ImportError
        try:
            ok, texte = self._controle()
        finally:
            sys.modules.clear()
            sys.modules.update(garde)
        self.assertFalse(ok)
        self.assertIn("combos", texte)

    def test_controle_signale_un_clavier_jamais_ouvert(self):
        """Le cas reel : les touches repondent, mais rien n'est tape.

        "interface non prete" a chaque appui est exact et inutilisable.
        Le controle doit nommer la cause : le mauvais port USB-C.
        """
        import runtime

        class InterfaceFermee:
            def is_open(self):
                return False

        with patch.object(runtime, 'safe_mode', False), \
             patch.object(runtime, 'config_mode', False), \
             patch.object(runtime, 'interface', InterfaceFermee()):
            ok, texte = self._controle()
        self.assertFalse(ok)
        self.assertIn("NE L'A PAS OUVERT", texte)
        self.assertIn("port USB-C", texte)

    def test_controle_accepte_un_clavier_ouvert(self):
        import runtime

        class InterfaceOuverte:
            def is_open(self):
                return True

        with patch.object(runtime, 'safe_mode', False), \
             patch.object(runtime, 'config_mode', False), \
             patch.object(runtime, 'interface', InterfaceOuverte()):
            _ok, texte = self._controle()
        self.assertIn("OUVERT par Windows", texte)

    def test_l_ecran_affiche_USB_quand_le_clavier_n_est_pas_ouvert(self):
        """Un « ... » ne disait rien. « USB? » envoie regarder le cable."""
        import main, runtime
        transport = Transport()
        transport.open = False          # Windows n'ouvre jamais l'interface
        etats = []

        def sleep_simule(ms):
            clock[0] += ms
            if clock[0] >= 7000:
                raise KeyboardInterrupt()

        import display as _display
        original = _display.Display.set_etat

        def espion(self, etat):
            etats.append(etat)
            original(self, etat)
        _display.Display.set_etat = espion
        sortie = io.StringIO()
        try:
            with patch.object(runtime, 'interface', transport), \
                 patch.object(runtime, 'safe_mode', False), \
                 patch.object(runtime, 'config_mode', False), \
                 patch.object(main, 'sleep_ms', sleep_simule), \
                 patch('sys.stdout', sortie):
                with self.assertRaises(KeyboardInterrupt):
                    main.run()
        finally:
            _display.Display.set_etat = original

        self.assertIn("USB?", etats, etats)
        # Et le REPL explique la cause, UNE seule fois.
        texte = sortie.getvalue()
        self.assertEqual(texte.count("N'A PAS OUVERT LE CLAVIER USB"), 1)
        self.assertIn("port USB-C", texte)
        self.assertIn("ESP-ROM:", texte)

    def test_controle_signale_deux_roles_sur_une_meme_broche(self):
        """L'erreur qu'on fait en corrigeant un numero a la main.

        La broche repond, mais a deux maitres : rien ne le signale, et le
        symptome est incomprehensible. Ici RGB_PIN vient marcher sur les
        pieds de la touche B4.
        """
        import diag
        ancienne = C.RGB_PIN
        C.RGB_PIN = C.BUTTON_PINS[3]
        try:
            self.assertTrue(diag.broches_en_double())
            ok, texte = self._controle()
        finally:
            C.RGB_PIN = ancienne
        self.assertFalse(ok)
        self.assertIn("DEUX choses", texte)
        self.assertIn("GPIO%d" % C.BUTTON_PINS[3], texte)

    def test_pas_de_doublon_dans_la_configuration_livree(self):
        """Le brochage du depot doit etre sain, variante active comprise."""
        import diag
        self.assertEqual(diag.broches_en_double(), [])

    def test_controle_est_vert_sur_une_configuration_saine(self):
        import runtime
        gardes = (C.HID_ENABLED, C.RGB_ENABLED, C.LINK_ENABLED, C.OLED_ENABLED)
        C.HID_ENABLED = C.RGB_ENABLED = C.LINK_ENABLED = C.OLED_ENABLED = True
        try:
            with patch.object(runtime, 'safe_mode', False), \
                 patch.object(runtime, 'config_mode', False), \
                 patch.object(runtime, 'interface', object()), \
                 patch.object(runtime, 'hid_error', None):
                ok, texte = self._controle()
        finally:
            (C.HID_ENABLED, C.RGB_ENABLED,
             C.LINK_ENABLED, C.OLED_ENABLED) = gardes
        self.assertTrue(ok, texte)
        self.assertIn("TOUT EST COHERENT", texte)


class BrochesAvantDeSouder(unittest.TestCase):
    """Le brochage de l'ESP32-S3, verifie AVANT le fer a souder.

    Souder une touche sur une broche de la flash ou de la PSRAM, c'est au
    mieux une touche muette, au pire une carte qui ne redemarre plus. Et
    une soudure, ca ne se defait pas d'un clic.
    """

    def test_les_broches_declarees_sont_toutes_utilisables(self):
        """Le controle qui compte : config.py ne cite aucune broche interdite."""
        import diag
        for numero in list(C.BUTTON_PINS) + [C.ESC_PIN, C.LED_PIN,
                                             C.TTP_PREVIOUS_PIN, C.TTP_NEXT_PIN,
                                             C.OLED_SDA, C.OLED_SCL, C.RGB_PIN]:
            verdict, raison = diag.verifier_broche(numero)
            self.assertEqual(verdict, "libre",
                             "GPIO%d : %s" % (numero, raison))

    def test_aucune_broche_n_est_utilisee_deux_fois(self):
        """Deux roles sur la meme broche : personne ne le voit au montage."""
        import diag
        declarees = (list(C.BUTTON_PINS)
                     + [C.ESC_PIN, C.LED_PIN, C.TTP_PREVIOUS_PIN, C.TTP_NEXT_PIN,
                        C.OLED_SDA, C.OLED_SCL, C.RGB_PIN])
        self.assertEqual(len(set(declarees)), len(declarees),
                         "doublon dans le brochage : %s" % sorted(declarees))
        # Et la table de diag voit bien tous ces roles.
        self.assertEqual(len(diag.broches_deja_prises()), len(set(declarees)))

    def test_usb_et_flash_sont_reservees(self):
        import diag
        # Les deux que tu m'as interdites des le depart.
        self.assertEqual(diag.verifier_broche(19)[0], "reservee")
        self.assertEqual(diag.verifier_broche(20)[0], "reservee")
        # La flash SPI du module : y toucher fait tomber la carte.
        for numero in range(26, 33):
            self.assertEqual(diag.verifier_broche(numero)[0], "reservee",
                             "GPIO%d" % numero)
        # La PSRAM octale d'un N16R8.
        for numero in range(33, 38):
            self.assertEqual(diag.verifier_broche(numero)[0], "reservee",
                             "GPIO%d" % numero)

    def test_les_numeros_qui_n_existent_pas(self):
        import diag
        for numero in (22, 23, 24, 25, 49, -1):
            self.assertEqual(diag.verifier_broche(numero)[0], "inexistante",
                             "GPIO%s" % numero)

    def test_la_console_serie_est_deconseillee_pas_interdite(self):
        """GPIO43/44 marchent, mais on y perd le REPL de Thonny."""
        import diag
        self.assertEqual(diag.verifier_broche(43)[0], "deconseillee")
        self.assertEqual(diag.verifier_broche(44)[0], "deconseillee")

    def test_les_broches_libres_excluent_ce_qui_sert_deja(self):
        import diag
        libres = diag.broches_libres()
        for numero in list(C.BUTTON_PINS) + [C.ESC_PIN, C.RGB_PIN]:
            self.assertNotIn(numero, libres)
        for numero in (19, 20, 26, 33, 43, 22):
            self.assertNotIn(numero, libres)
        self.assertTrue(libres, "aucune broche de repli : suspect")

    def test_diag_ne_touche_JAMAIS_une_broche_reservee(self):
        """Le vrai filet : creer un Pin sur la flash suffit a tout casser.

        On declare volontairement une touche sur GPIO30 (SPICLK) et on
        verifie que diag.broches() la signale SANS jamais construire le
        Pin - avec un faux Pin qui explose si on l'appelle.
        """
        import diag
        touchees = []
        original = Pin.__init__

        def espion(self, n, mode=None, pull=None, value=None):
            if n in tuple(range(26, 38)) + (19, 20):
                raise AssertionError("broche reservee GPIO%d touchee !" % n)
            touchees.append(n)
            original(self, n, mode, pull)

        anciennes = C.BUTTON_PINS
        C.BUTTON_PINS = (4, 5, 6, 30, 12, 13)      # GPIO30 = flash SPICLK
        Pin.__init__ = espion
        try:
            diag.broches(secondes=0)
        finally:
            Pin.__init__ = original
            C.BUTTON_PINS = anciennes

        self.assertNotIn(30, touchees)
        # Les cinq autres touches, elles, ont bien ete lues.
        for numero in (4, 5, 6, 12, 13):
            self.assertIn(numero, touchees)

    def test_diag_broches_refuse_quand_une_broche_est_interdite(self):
        import diag
        anciennes = C.BUTTON_PINS
        C.BUTTON_PINS = (4, 5, 6, 19, 12, 13)      # GPIO19 = USB D-
        try:
            self.assertFalse(diag.broches(secondes=0))
        finally:
            C.BUTTON_PINS = anciennes
        self.assertTrue(diag.broches(secondes=0))


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
                self.vues = []

            def __setitem__(self, index, valeur):
                self.pixels[index] = valeur

            def __getitem__(self, index):
                return self.pixels[index]

            def write(self):
                self.ecritures += 1
                # On retient l'instant : c'est ce qui permet de verifier
                # QUAND la LED a reagi, et pas seulement qu'elle a reagi.
                self.vues.append((clock[0], tuple(self.pixels)))
                NeoPixel.derniere = self

        NeoPixel.derniere = None
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

    # --- ce que le REPL annonce au demarrage ----------------------------
    def test_le_demarrage_annonce_l_etat_des_led(self):
        """Un ruban noir sans un mot dans le REPL fait chercher la panne
        dans le cablage alors que le firmware n'a jamais eu l'ordre de
        l'allumer. C'est arrive."""
        import contextlib, io as _io, rgb

        with contextlib.redirect_stdout(_io.StringIO()) as sortie:
            rgb.Rgb()
        annonce = sortie.getvalue()
        self.assertIn("RGB", annonce)
        self.assertIn("6 LED", annonce)
        self.assertIn("GPIO%d" % C.RGB_PIN, annonce)
        self.assertIn("GRB", annonce)

    def test_le_demarrage_dit_pourquoi_rien_ne_s_allume(self):
        import contextlib, io as _io, rgb
        self._regler(RGB_ENABLED=False)
        with contextlib.redirect_stdout(_io.StringIO()) as sortie:
            objet = rgb.Rgb()
        self.assertFalse(objet.actif)
        # Le message doit nommer le reglage a changer, pas juste dire non.
        self.assertIn("RGB_ENABLED", sortie.getvalue())
        self.assertIn("config.py", sortie.getvalue())

    # --- les couleurs --------------------------------------------------
    def test_chaque_profil_a_sa_couleur(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["CIVIL3D"])
        objet.tick(100)
        attendu = tuple(C.RGB_COULEURS["CIVIL3D"])
        r, v, b = self._repos(attendu)
        # Les WS2812 attendent VERT, ROUGE, BLEU.
        for pixel in objet.materiel.pixels:
            self.assertEqual(pixel, (v, r, b))

    def test_ordre_des_couleurs_configurable(self):
        self._regler(RGB_ORDRE="RGB")
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["CIVIL3D"])
        objet.tick(100)
        r, v, b = self._repos(C.RGB_COULEURS["CIVIL3D"])
        self.assertEqual(objet.materiel.pixels[0], (r, v, b))

    def test_profil_inconnu_prend_la_couleur_par_defaut(self):
        objet = self._rgb()
        objet.profil(None)
        objet.tick(100)
        r, v, b = self._repos(C.RGB_COULEUR_DEFAUT)
        self.assertEqual(objet.materiel.pixels[0], (v, r, b))

    def _repos(self, couleur):
        """La couleur AU REPOS : le profil attenue par la reserve d'appui.

        Ce n'est pas la couleur pleine. RGB_RESPIRATION_MAX garde de la
        place au-dessus, sans quoi un appui sur une couleur dont un canal
        vaut 255 ne pourrait plus rien eclaircir.
        """
        import rgb
        return rgb.limiter(rgb._attenuer(
            couleur, getattr(C, "RGB_RESPIRATION_MAX", 0.55)))

    def _clarte(self, objet, index):
        return sum(objet.materiel.pixels[index])

    def test_un_appui_intensifie_sa_touche_tout_de_suite(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        objet.tick(0)
        repos = self._clarte(objet, 3)

        objet.touche(3, 100)
        objet.tick(100)               # le tout premier tour de boucle
        self.assertGreater(self._clarte(objet, 3), repos,
                           "la LED n'a pas reagi des le premier tour")
        # Et seulement celle-la.
        self.assertEqual(self._clarte(objet, 2), repos)

    def test_deux_appuis_montent_deux_fois_plus_haut(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        objet.tick(0)

        objet.touche(3, 10)
        objet.tick(10)
        un = self._clarte(objet, 3)
        objet.touche(3, 20)           # deuxieme appui, coup sur coup
        objet.tick(30)
        deux = self._clarte(objet, 3)
        self.assertGreater(deux, un, "le second appui n'a rien ajoute")

    def test_la_retombee_est_progressive_et_revient_au_calme(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        objet.tick(0)
        repos = self._clarte(objet, 1)

        objet.touche(1, 10)
        objet.tick(10)
        etapes = []
        instant = 10
        while instant < 10 + C.RGB_RETOMBEE_MS + 200:
            instant += C.RGB_MS
            objet.tick(instant)
            etapes.append(self._clarte(objet, 1))

        # Elle ne retombe pas d'un coup : plusieurs valeurs intermediaires.
        intermediaires = set(v for v in etapes if repos < v < etapes[0])
        self.assertGreater(len(intermediaires), 5,
                           "la retombee est brutale : %d paliers"
                           % len(intermediaires))
        # Elle ne remonte jamais en chemin.
        for precedent, suivant in zip(etapes, etapes[1:]):
            self.assertLessEqual(suivant, precedent + 1)
        # Et on finit par revenir a la couleur du profil.
        self.assertEqual(etapes[-1], repos)

    def test_l_empilement_est_plafonne(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])
        for n in range(20):
            objet.touche(0, 10)       # vingt appuis, sans laisser retomber
        self.assertLessEqual(objet.niveaux[0], C.RGB_IMPULSION_MAX)

    def test_meme_a_fond_le_plafond_de_courant_tient(self):
        """LA verification qui compte : l'impulsion ne peut pas faire
        redemarrer la carte a force d'appuyer."""
        objet = self._rgb()
        objet.profil((255, 255, 255))     # le pire cas, du blanc
        for n in range(20):
            objet.touche(2, 10)
        objet.tick(10)
        for canal in objet.materiel.pixels[2]:
            self.assertLessEqual(canal, C.RGB_LUMINOSITE,
                                 "le plafond de courant est franchi")

    def test_panne_hid_passe_au_rouge_et_revient(self):
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["BLENDER"])
        objet.tick(100)
        objet.etat("ERR")
        objet.tick(200)
        r, v, b = self._repos(C.RGB_COULEUR_ERREUR)
        self.assertEqual(objet.materiel.pixels[0], (v, r, b))
        objet.etat("HID")
        objet.tick(300)
        r, v, b = self._repos(C.RGB_COULEURS["BLENDER"])
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
        self._regler(RGB_RESPIRATION_MS=4000, RGB_RESPIRATION_MIN=0.35,
                     RGB_RESPIRATION_MAX=0.80)
        creux = rgb.respiration(0)
        milieu = rgb.respiration(2000)
        self.assertAlmostEqual(creux, 0.35, places=3)
        # Le sommet est le PLAFOND, pas 1.0 : le reste est la reserve de
        # l'appui, sans laquelle on ne voit plus quelle touche a servi.
        self.assertAlmostEqual(milieu, 0.80, places=3)
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

    def test_l_impulsion_s_ajoute_a_la_respiration(self):
        # Un appui doit se voir autant en haut qu'en bas du cycle de
        # respiration : l'impulsion s'AJOUTE, elle ne multiplie pas.
        self._regler(RGB_RESPIRATION=True, RGB_RESPIRATION_MS=4000)
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["WORD"])

        objet.tick(0)                       # creux de la respiration
        creux = self._clarte(objet, 2)
        objet.touche(2, 0)
        objet.tick(0)
        gain_en_bas = self._clarte(objet, 2) - creux

        objet2 = self._rgb()
        objet2.profil(C.RGB_COULEURS["WORD"])
        # On avance par petits pas, comme la vraie boucle : un saut d'un
        # seul coup serait ignore, c'est justement la garde anti-saut.
        for instant in range(0, 2001, 100):
            objet2.tick(instant)            # jusqu'au sommet du cycle
        sommet = self._clarte(objet2, 2)
        objet2.touche(2, 2000)
        objet2.tick(2000)
        gain_en_haut = self._clarte(objet2, 2) - sommet

        self.assertGreater(sommet, creux)   # la respiration fait son travail
        self.assertAlmostEqual(gain_en_bas, gain_en_haut, delta=3)

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

    # --- la boucle complete, LED allumees --------------------------------
    def test_la_boucle_principale_tourne_avec_les_led_actives(self):
        """Tout le firmware, RGB_ENABLED = True, comme sur la carte.

        C'est le seul test qui fait tourner main.run() avec les LED
        reellement pilotees : rien ne sert de savoir que rgb.py fonctionne
        seul si l'activer fait tomber la boucle principale.
        """
        import main, runtime, profiles as P
        self._regler(RGB_RESPIRATION=True)
        Pin.levels = {}
        clock[0] = 0
        transport = Transport()

        def sommeil_simule(ms):
            clock[0] += ms
            # Un appui sur B3, puis un changement de profil, puis ESC.
            Pin.levels[6] = 0 if 2600 <= clock[0] < 2660 else 1
            Pin.levels[11] = 1 if 2700 <= clock[0] < 2780 else 0
            Pin.levels[14] = 0 if 2900 <= clock[0] < 2960 else 1
            if clock[0] >= 3400:
                raise KeyboardInterrupt()

        with patch.object(runtime, 'interface', transport), \
             patch.object(runtime, 'safe_mode', False), \
             patch.object(main, 'sleep_ms', sommeil_simule):
            with self.assertRaises(KeyboardInterrupt):
                main.run()

        # Le ruban a bien ete pilote pendant toute la boucle.
        bande = sys.modules['neopixel'].NeoPixel.derniere
        self.assertIsNotNone(bande, "aucune LED n'a ete initialisee")
        self.assertGreater(bande.ecritures, 10,
                           "le ruban n'a pas ete rafraichi")
        # Il a pris la couleur du profil de depart, puis celle du suivant.
        self.assertGreater(len(set(v[1] for v in bande.vues)), 1,
                           "la couleur n'a jamais change")
        # Et il est ETEINT a l'arret : main.run() passe par rgb.close().
        self.assertEqual(bande.pixels[0], (0, 0, 0),
                         "les LED sont restees allumees apres l'arret")

    def test_la_led_suit_le_doigt_et_pas_la_macro(self):
        """La panne constatee : un quart de seconde de retard a l'appui.

        La touche 1 a un double appui : le firmware attend donc
        GESTE_DOUBLE_MS avant de savoir quelle macro envoyer. Tant que la
        LED etait allumee par declencher(), elle heritait de cette
        attente. Elle doit maintenant reagir au FRONT D'APPUI.
        """
        import main, runtime
        self._regler(RGB_RESPIRATION=False)
        Pin.levels = {}
        clock[0] = 0
        transport = Transport()
        appui, relache = 2600, 2660

        def sommeil_simule(ms):
            clock[0] += ms
            Pin.levels[4] = 0 if appui <= clock[0] < relache else 1
            if clock[0] >= 3400:
                raise KeyboardInterrupt()

        with patch.object(runtime, 'interface', transport), \
             patch.object(runtime, 'safe_mode', False), \
             patch.object(main, 'sleep_ms', sommeil_simule):
            with self.assertRaises(KeyboardInterrupt):
                main.run()

        bande = sys.modules['neopixel'].NeoPixel.derniere
        # La macro de l'appui court ne part qu'a relache + GESTE_DOUBLE_MS.
        macro = relache + C.GESTE_DOUBLE_MS
        tot = [pixels for instant, pixels in bande.vues
               if appui <= instant < appui + 60]
        self.assertTrue(tot, "aucun rafraichissement dans les 60 ms")
        # Dans ces 60 premieres millisecondes, la LED 1 est deja plus
        # claire que ses voisines - bien avant que la macro ne parte.
        self.assertTrue(
            any(sum(image[0]) > sum(image[1]) for image in tot),
            "la LED n'a pas reagi avant %d ms" % (macro - appui))

    # --- l'appui doit se VOIR, meme au sommet de la respiration ----------
    def test_un_appui_se_voit_au_sommet_de_la_respiration(self):
        """Defaut signale a l'usage : au maximum de la respiration, on ne
        voyait plus quelle touche on venait d'appuyer.

        La cause n'etait PAS "pas assez lumineux". Une couleur dont un
        canal vaut 255 - le bleu de CIVIL3D - touchait deja le plafond de
        courant au sommet du cycle : l'appui ne pouvait plus l'eclaircir,
        il ne faisait que DELAVER les autres canaux. Sur un bleu pur, il
        n'aurait rien fait du tout.
        """
        import rgb
        sommet = C.RGB_RESPIRATION_MAX
        for nom, couleur in C.RGB_COULEURS.items():
            repos = rgb.limiter(rgb._attenuer(couleur, sommet))
            appui = rgb.limiter(rgb._attenuer(couleur,
                                              sommet + C.RGB_IMPULSION))
            for canal in range(3):
                if couleur[canal] == 0:
                    self.assertEqual(appui[canal], 0, nom)
                else:
                    self.assertGreater(appui[canal], repos[canal],
                                       "%s : canal %d ne monte pas"
                                       % (nom, canal))
            # Et le gain est franc, pas marginal : au moins +60 %.
            self.assertGreater(sum(appui), sum(repos) * 1.6, nom)

    def test_un_appui_amene_la_touche_a_sa_couleur_pleine(self):
        """0.55 + 0.45 = 1.00, et ce n'est pas un hasard.

        Le sommet de la respiration plus l'impulsion donnent exactement la
        couleur nominale du profil : l'appui est donc previsible, et la
        TEINTE ne bouge pas - c'est de la clarte qu'on ajoute, pas du
        blanc.
        """
        import rgb
        self.assertAlmostEqual(C.RGB_RESPIRATION_MAX + C.RGB_IMPULSION, 1.0,
                               places=9)
        for nom, couleur in C.RGB_COULEURS.items():
            appui = rgb.limiter(rgb._attenuer(
                couleur, C.RGB_RESPIRATION_MAX + C.RGB_IMPULSION))
            self.assertEqual(appui, rgb.limiter(couleur), nom)

    def test_une_couleur_pure_reagit_aussi(self):
        """Le pire cas : un bleu pur (0, 0, 255), un seul canal a fond.

        C'est celui qui ne reagissait pas du tout a l'appui - et celui
        qu'un utilisateur choisit tres naturellement dans le selecteur de
        couleur de la page web.
        """
        import rgb
        for couleur in ((0, 0, 255), (255, 0, 0), (0, 255, 0),
                        (255, 255, 255)):
            repos = rgb.limiter(rgb._attenuer(couleur, C.RGB_RESPIRATION_MAX))
            appui = rgb.limiter(rgb._attenuer(
                couleur, C.RGB_RESPIRATION_MAX + C.RGB_IMPULSION))
            self.assertGreater(sum(appui), sum(repos) * 1.6, str(couleur))

    def test_la_respiration_reste_entre_son_plancher_et_son_plafond(self):
        import rgb
        vus = []
        for phase in range(0, C.RGB_RESPIRATION_MS * 2, 13):
            facteur = rgb.respiration(phase)
            self.assertGreaterEqual(facteur, C.RGB_RESPIRATION_MIN - 1e-9)
            self.assertLessEqual(facteur, C.RGB_RESPIRATION_MAX + 1e-9,
                                 "la respiration mange la reserve de l'appui")
            vus.append(facteur)
        # Elle parcourt bien toute sa plage, elle ne reste pas plate.
        self.assertLess(min(vus), C.RGB_RESPIRATION_MIN + 0.01)
        self.assertGreater(max(vus), C.RGB_RESPIRATION_MAX - 0.01)

    def test_la_reserve_de_l_appui_ne_depasse_pas_le_plafond_de_courant(self):
        """La securite d'origine tient toujours : six LED en blanc, appui
        compris, ne doivent pas approcher les 500 mA du port USB."""
        import rgb
        pire = rgb.limiter(rgb._attenuer(
            (255, 255, 255), C.RGB_RESPIRATION_MAX + C.RGB_IMPULSION_MAX))
        # 20 mA par canal a fond, trois canaux, six LED.
        courant = sum(pire) / 255.0 * 20 * C.RGB_COUNT
        self.assertLess(courant, 200, "%d mA pour les LED seules" % courant)

    # --- le test de cablage du REPL --------------------------------------
    def test_diag_rgb_parcourt_toutes_les_led(self):
        """diag.rgb() sert a compter les LED qui repondent vraiment."""
        import diag
        vues = []
        module = sys.modules['neopixel']
        original = module.NeoPixel.write

        def espion(self):
            vues.append(list(self.pixels))
            original(self)
        module.NeoPixel.write = espion
        try:
            diag.rgb(nb=4, broche=16, luminosite=10)
        finally:
            module.NeoPixel.write = original

        # Chaque LED a ete allumee seule, dans l'ordre.
        for index in range(4):
            attendu = [(0, 0, 0)] * 4
            attendu[index] = (10, 10, 10)
            self.assertIn(attendu, vues, "la LED %d n'a pas ete testee"
                          % (index + 1))
        # Et tout est eteint a la fin : on n'abandonne jamais les LED
        # allumees apres un diagnostic.
        self.assertEqual(vues[-1], [(0, 0, 0)] * 4)

    def test_diag_rgb_pin_n_essaie_que_des_broches_libres(self):
        """Le balayage ne doit pas ecraser l'ecran ni la flash.

        Il pilote des GPIO en SORTIE : taper sur le SDA de l'ecran ou sur
        l'horloge de la flash pendant qu'on cherche un fil, ce serait
        transformer un diagnostic en panne.
        """
        import diag
        vues = []
        module = sys.modules['neopixel']
        original = module.NeoPixel.__init__

        def espion(self, broche, nb):
            vues.append(broche.n if hasattr(broche, "n") else broche)
            original(self, broche, nb)
        module.NeoPixel.__init__ = espion
        try:
            diag.rgb_pin(secondes=0, luminosite=5)
        finally:
            module.NeoPixel.__init__ = original

        self.assertTrue(vues, "aucune broche essayee")
        # La broche configuree passe en premier : c'est la plus probable.
        self.assertEqual(vues[0], C.RGB_PIN)
        prises = diag.broches_deja_prises()
        for numero in vues:
            self.assertEqual(diag.verifier_broche(numero)[0], "libre",
                             "GPIO%d n'est pas libre" % numero)
            role = prises.get(numero)
            self.assertIn(role, (None, "donnees des LED RGB"),
                          "GPIO%d sert deja a : %s" % (numero, role))

    def test_diag_rgb_saute_decale_bien_le_ruban(self):
        """Une premiere LED grillee ne transmet plus rien a ses voisines.

        On pilote alors le ruban comme s'il en avait une de plus, et on
        envoie du noir aux mortes. Le test verifie que la LED allumee est
        bien DECALEE, et qu'aucune des ignorees ne s'allume jamais.
        """
        import diag
        vues = []
        module = sys.modules['neopixel']
        original = module.NeoPixel.write

        def espion(self):
            vues.append(list(self.pixels))
            original(self)
        module.NeoPixel.write = espion
        try:
            diag.rgb_saute(2, nb=4, broche=16, luminosite=9)
        finally:
            module.NeoPixel.write = original

        # Le ruban est pilote avec 2 + 4 LED.
        self.assertTrue(all(len(image) == 6 for image in vues), vues)
        # Les deux ignorees restent NOIRES a chaque envoi, sans exception.
        for image in vues:
            self.assertEqual(image[0], (0, 0, 0))
            self.assertEqual(image[1], (0, 0, 0))
        # Et chacune des quatre autres a bien ete allumee, seule.
        for index in range(4):
            attendu = [(0, 0, 0)] * 6
            attendu[2 + index] = (9, 9, 9)
            self.assertIn(attendu, vues, "LED %d non testee" % (index + 1))
        # Tout est eteint en partant.
        self.assertEqual(vues[-1], [(0, 0, 0)] * 6)

    def test_diag_rgb_respecte_l_ordre_des_octets(self):
        # Quand il annonce ROUGE, c'est bien l'octet rouge qui est mis a
        # l'endroit ou la puce l'attend - sinon le test induirait en
        # erreur celui qui regle justement RGB_ORDRE.
        import diag
        self._regler(RGB_ORDRE="GRB")
        vues = []
        module = sys.modules['neopixel']
        original = module.NeoPixel.write

        def espion(self):
            vues.append(self.pixels[0])
            original(self)
        module.NeoPixel.write = espion
        try:
            diag.rgb(nb=1, broche=16, luminosite=10)
        finally:
            module.NeoPixel.write = original
        # GRB : le rouge est le DEUXIEME octet.
        self.assertIn((0, 10, 0), vues)     # ROUGE annonce
        self.assertIn((10, 0, 0), vues)     # VERT annonce
        self.assertIn((0, 0, 10), vues)     # BLEU annonce

    def test_diag_rgb_eteint_tout_meme_si_on_l_interrompt(self):
        import diag
        module = sys.modules['neopixel']
        original = module.NeoPixel.write
        compteur = [0]

        def espion(self):
            compteur[0] += 1
            if compteur[0] == 3:
                raise KeyboardInterrupt()
            original(self)
        module.NeoPixel.write = espion
        try:
            diag.rgb(nb=4, broche=16, luminosite=10)   # ne doit rien lever
        finally:
            module.NeoPixel.write = original

    def test_diag_rgb_sans_neopixel_ne_plante_pas(self):
        import diag
        del sys.modules['neopixel']
        diag.rgb(nb=4, broche=16)      # affiche un message, c'est tout

    # --- le montage a une seule LED RGB ---------------------------------
    def test_montage_pwm_anode_commune(self):
        self._regler(RGB_TYPE="PWM", RGB_PIN_R=16, RGB_PIN_V=17,
                     RGB_PIN_B=18, RGB_ANODE_COMMUNE=True)
        objet = self._rgb()
        objet.profil(C.RGB_COULEURS["CIVIL3D"])
        objet.tick(100)
        r, v, b = self._repos(C.RGB_COULEURS["CIVIL3D"])
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

    def test_les_suites_d_actions_traversent_la_page_web(self):
        """Les pages web gardaient autrefois UNE seule action par geste :
        une valeur d'usine qui en contenait deux etait tronquee en silence
        au premier "Enregistrer". Ce n'est plus le cas, mais l'invariant
        merite d'etre garde : ce qui entre doit ressortir a l'identique,
        quelle que soit la longueur de la suite."""
        import profiles as P
        import store
        for nom, touches in P.PROFILES.items():
            for index, (label, gestes) in enumerate(touches):
                for geste, actions in gestes.items():
                    aller = store.actions_vers_json(actions)
                    self.assertEqual(len(aller), len(actions))
                    retour = store.actions_depuis_json(aller)
                    self.assertEqual(
                        retour, actions,
                        "%s B%d %s : la suite ne survit pas a l'aller-retour"
                        % (nom, index + 1, geste))

        # Et une suite de trois etapes, avec une pause, passe aussi.
        suite = [("text_enter", "_PURGE"), ("pause", "500"),
                 ("combo", ("CTRL", "S"))]
        self.assertEqual(
            store.actions_depuis_json(store.actions_vers_json(suite)), suite)

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
        # Une liste deroulante par etape : 6 touches x 3 gestes par
        # profil, plus une par etape de combinaison.
        etapes_combos = sum(
            max(1, len(combo["actions"]))
            for bloc in configuration["profils"].values()
            for combo in bloc.get("combos", []))
        self.assertEqual(vu["listes"], profils * 6 * 3 + etapes_combos)
        self.assertIn("source", vu["src"])
        self.assertIn("appuis", vu["cnt"])
        # Les logiciels : une ligne d'en-tete, une par logiciel, une pour
        # le repli.
        self.assertEqual(vu["apps"],
                         len(configuration["apps"]["liste"]) + 2)
        self.assertFalse(vu["texte_vide"])

    def test_une_lecture_impossible_explique_quoi_verifier(self):
        """Cas reel : la page n'affichait qu'une ligne rouge, sans piste.

        charger() sortait avant render() quand l'API renvoyait une erreur,
        si bien que la carte d'explication - qui dit exactement quoi
        verifier - etait supprimee PILE au moment ou elle servait. Le
        conseil existait, personne ne le voyait.
        """
        vu = self._construire(
            {"erreur": "macropad non connecte : aucun port Espressif "
                       "(VID 0x303A) trouve."})

        # La raison exacte est affichee, pas un message generique.
        self.assertIn("0x303A", vu["erreur_texte"])
        # Et surtout, la carte d'explication est la.
        self.assertEqual(vu["cartes"], 1)
        self.assertIn("Aucun profil recu", vu["texte_profs"])
        for piste in ("USB NATIF", "Thonny", "SAFE MODE"):
            self.assertIn(piste, vu["texte_profs"], piste)
        # Les deux pastilles de l'en-tete ne restent pas sur "...".
        self.assertNotIn("...", vu["erreur_src"])

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

        # Un bouton "+ etape" par geste : 6 touches x 3 gestes.
        self.assertEqual(vu["boutons_etape"], 18)
        # L'etape ajoutee est bien partie, a la suite de la premiere.
        self.assertEqual(vu["touche1_etapes"], 2)
        self.assertEqual(vu["touche1_etape2"],
                         {"type": "pause", "valeur": "500"})
        # La touche 6 ne doit surtout pas avoir bouge.
        self.assertEqual(vu["derniere_touche_label"], "MOVE")
        # Meme verification sur la table des logiciels.
        self.assertEqual(vu["app2_abrege"], "AbRg")
        self.assertEqual(vu["app1_abrege"], "C3D")
        self.assertIn("Enregistre", vu["message"])

    def test_les_combinaisons_s_editent_et_repartent_entieres(self):
        """Elles s'affichent, se modifient, et survivent a l'enregistrement.

        Le risque propre aux combinaisons : une page qui les ignore les
        RENVERRAIT VIDES a l'enregistrement, et effacerait en silence tout
        ce que la carte avait. On verifie donc ce qui part reellement sur
        le fil, pas ce qui est dessine.
        """
        import store, profiles as P
        configuration = store.vers_json(6)
        vu = self._construire(configuration)

        nom = configuration["ordre"][vu["carte_combos"]]
        attendues = configuration["profils"][nom]["combos"]
        self.assertEqual(vu["combos_affiches"], len(attendues))
        # Les numeros affiches sont ceux du pad : "3+4", pas "2+3".
        self.assertEqual(vu["combo_touches_lues"],
                         "+".join(str(n) for n in attendues[0]["touches"]))

        # Tout est reparti, et en entier.
        self.assertEqual(vu["combos_envoyes"], len(attendues))
        # La saisie mal ecrite "5 et 6" a ete comprise...
        self.assertEqual(vu["combo1"]["touches"], [5, 6])
        self.assertEqual(vu["combo1"]["label"], "ESSAI")
        # ...et la derniere combinaison n'a surtout pas bouge : c'est le
        # piege du « var » de boucle, deja rencontre sur les touches.
        self.assertEqual(vu["combo_dernier_libelle"],
                         vu["combo_dernier_libelle_avant"])
        self.assertEqual(vu["combo_dernier_libelle"], attendues[-1]["label"])

        # Un profil qui n'a aucune combinaison n'en renvoie pas une seule,
        # mais renvoie bien une liste vide plutot que rien : sinon la
        # carte remettrait celles d'usine a chaque enregistrement.
        self.assertEqual(vu["combos_profil_sans"], 0)

    def test_l_enregistreur_transforme_les_frappes_en_etapes(self):
        """Tu tapes ta sequence, la page en fait des etapes.

        Trois regles a verifier, et elles portent tout :
          - les caracteres ordinaires s'ACCUMULENT en une seule etape ;
          - Entree juste apres du texte donne "texte + Entree" ;
          - une attente reelle devient une etape de pause.
        """
        import store
        vu = self._construire(store.vers_json(6))

        self.assertTrue(vu["rec_en_cours"], "l'enregistrement n'a pas demarre")
        self.assertTrue(vu["rec_termine"], "l'enregistrement ne s'arrete pas")
        self.assertEqual(vu["rec_etapes"], [
            {"type": "text_enter", "valeur": "_PL"},   # 3 frappes, 1 etape
            {"type": "pause", "valeur": "900"},        # l'attente reelle
            {"type": "combo", "valeur": "CTRL+S"},     # Ctrl seul ignore
            {"type": "key", "valeur": "F5"},
        ])
        self.assertIn("4 etape", vu["rec_message"])

    def test_l_enregistreur_ne_produit_que_des_macros_valables(self):
        """Le controle qui compte : ce qu'il fabrique doit etre TAPABLE.

        Une sequence enregistree qui serait refusee a l'enregistrement -
        ou pire, qui planterait le firmware - transformerait un raccourci
        en piege. On la fait donc passer par le meme chemin que n'importe
        quelle macro ecrite a la main.
        """
        import store
        vu = self._construire(store.vers_json(6))
        actions = store.actions_depuis_json(vu["rec_etapes"])
        self.assertEqual(actions, [("text_enter", "_PL"),
                                   ("pause", "900"),
                                   ("combo", ("CTRL", "S")),
                                   ("key", "F5")])
        self.assertTrue(compile_actions(actions, C.KEYBOARD_LAYOUT))
        # Et la configuration complete reste acceptee par le firmware.
        profils, ordre, titres, couleurs, combos, apps, repli = store.defauts()
        profils["CIVIL3D"][1][1]["long"] = actions
        self.assertEqual(store.verifier(profils, ordre, 6, combos), [])

    def test_echap_arrete_l_enregistrement_sans_s_enregistrer(self):
        """Le reflexe de celui qui veut annuler ne doit pas produire d'ESC."""
        import store
        vu = self._construire(store.vers_json(6))
        self.assertTrue(vu["rec_echap_arrete"])
        self.assertEqual(vu["rec_echap_etapes"],
                         [{"type": "text", "valeur": "a"}])

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

    def test_la_capture_de_raccourci_donne_des_noms_valides(self):
        """Tu cliques, tu appuies, la page ecrit le nom a ta place.

        Le point delicat : les noms produits doivent etre EXACTEMENT ceux
        que comprend le firmware. Une page qui ecrirait DELETE la ou
        layouts.py attend SUPPR fabriquerait des macros refusees a
        l'enregistrement, sans que rien n'explique pourquoi.
        """
        import store
        vu = self._construire(store.vers_json(6))
        capture = vu["capture"]

        self.assertEqual(capture["ctrl_maj_p"], "CTRL+SHIFT+P")
        self.assertEqual(capture["f5"], "F5")
        self.assertEqual(capture["win_e"], "WIN+E")
        self.assertEqual(capture["ctrl_1"], "CTRL+1")
        self.assertEqual(capture["suppr"], "SUPPR")
        self.assertEqual(capture["fleche"], "UP")
        self.assertEqual(capture["echap"], "ESC")
        # Un modificateur seul : c'est ce qu'il faut pour un "maintien".
        self.assertEqual(capture["ctrl_seul"], "CTRL")
        self.assertEqual(capture["maj_seul"], "SHIFT")
        # AltGr se presente comme Ctrl+Alt sous Windows : il ne doit pas
        # ressortir en "CTRL+ALT".
        self.assertEqual(capture["altgr"], "ALTGR")
        # Une touche exotique ne produit rien plutot qu'un nom invente.
        self.assertEqual(capture["inconnu"], "")

        # LA verification : le firmware accepte-t-il ces noms ?
        from layouts import compile_actions
        for cle, nom in capture.items():
            if not nom:
                continue
            touches = tuple(nom.split("+"))
            compile_actions([("combo", touches)], C.KEYBOARD_LAYOUT)

    def test_tous_les_noms_du_tableau_de_capture_sont_connus(self):
        """Le tableau complet, pas seulement ceux qu'on a essayes."""
        from layouts import key_code
        tableaux = self.re.findall(r"var (?:TOUCHES|MODIFS)=\{(.*?)\};",
                                   self.source, self.re.S)
        self.assertEqual(len(tableaux), 2, "tableaux de capture introuvables")
        noms = set()
        for tableau in tableaux:
            noms.update(self.re.findall(r'"([A-Z0-9]+)"', tableau))
        self.assertGreater(len(noms), 15, "tableau de capture trop court")
        for nom in noms:
            key_code(nom, C.KEYBOARD_LAYOUT)      # leve si inconnu
        # Et les formes fabriquees : lettres, chiffres, touches de fonction.
        for nom in ["A", "Z", "0", "9"] + ["F%d" % n for n in range(1, 13)]:
            key_code(nom, C.KEYBOARD_LAYOUT)

    def test_la_restauration_d_une_sauvegarde(self):
        """Le bouton Telecharger existait ; il manquait celui du retour."""
        import store
        vu = self._construire(store.vers_json(6))

        self.assertTrue(vu["restaure_bonne"])
        self.assertIn("4 profils", vu["message_restaure"])
        # Elle CHARGE le formulaire sans appliquer : le message le dit.
        self.assertIn("Enregistrer", vu["message_restaure"])
        self.assertEqual(vu["cartes_apres_restauration"], 4)

        # Un fichier illisible ou etranger est refuse, sans rien casser.
        self.assertFalse(vu["restaure_cassee"])
        self.assertFalse(vu["restaure_etrangere"])
        self.assertIn("sauvegarde du macropad", vu["message_refus"])

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
        (profils, ordre, titres, couleurs, combos,
         apps, repli) = store.depuis_json(ancien, 6)
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
        profils, _, _, _, _, _, _ = store.depuis_json(recent, 6)
        self.assertEqual(profils["WORD"][0][1]["court"],
                         [("combo", ("CTRL", "B"))])


if __name__=='__main__': unittest.main(verbosity=2)
