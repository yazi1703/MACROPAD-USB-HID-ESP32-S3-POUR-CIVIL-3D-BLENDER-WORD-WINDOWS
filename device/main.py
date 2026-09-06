# -*- coding: utf-8 -*-
"""
main.py - Le chef d'orchestre. Lancé automatiquement après boot.py.

=====================================================================
LE PRINCIPE : UNE SEULE BOUCLE, JAMAIS D'ATTENTE
=====================================================================
Tout le macropad tient dans une seule boucle qui tourne environ 500 fois
par seconde. À chaque tour, on fait un tout petit peu de chaque travail :

    1. lire les entrées          (quelques microsecondes)
    2. traiter ESC en priorité
    3. traiter les profils et les macros
    4. envoyer AU PLUS un paquet clavier
    5. mettre à jour la LED
    6. envoyer AU PLUS une page d'écran
    7. dormir 2 ms, et on recommence

C'est ce qu'on appelle une boucle coopérative : chaque tâche prend un
petit morceau de temps puis rend la main volontairement. Aucune tâche ne
peut donc bloquer les autres. C'est pour cela qu'écrire une commande de
16 caractères (400 ms) n'empêche jamais le bouton ESC de répondre.

L'ordre des étapes n'est pas anodin : ESC est traité en tout premier.

=====================================================================
LES TROIS SECURITES AU DEMARRAGE
=====================================================================
1. boot.py n'a même pas créé le clavier si tu maintenais B1 (SAFE MODE).
2. Toutes les macros sont traduites AVANT la première touche : une macro
   mal écrite fait échouer le démarrage avec un message clair, plutôt que
   de taper n'importe quoi.
3. Pendant BOOT_GUARD_MS (2,5 s), les touches sont ignorées. Tu as le
   temps de débrancher si quelque chose se passe mal.
"""

from time import ticks_ms, ticks_diff, sleep_ms
import config as C
import runtime
from inputs import Inputs
from profiles import ProfileManager, PROFILES, TESTS
from display import Display
from hid_keyboard import HIDKeyboard
from layouts import compile_actions


def run():
    display = Display()

    # ---------------------------------------------------------------
    # Cas particulier : SAFE MODE
    # ---------------------------------------------------------------
    # boot.py n'a pas créé le clavier. On l'affiche et on rend la main au
    # REPL pour que tu puisses réparer tes fichiers dans Thonny.
    if runtime.safe_mode:
        display.message("SAFE MODE", "HID DISABLED")
        display.flush_startup()
        print("REPL disponible. Diagnostics : import diag; diag.run()")
        return

    manager = ProfileManager(C.PROFILES_ORDER, C.DEFAULT_PROFILE)

    # Vérification de TOUTES les macros avant la moindre frappe.
    # Si une macro contient un caractère impossible à taper, on préfère
    # une erreur ici plutôt qu'une commande à moitié écrite dans Civil 3D.
    for name in C.PROFILES_ORDER:
        for label, actions in PROFILES[name]:
            compile_actions(actions, C.KEYBOARD_LAYOUT)
    if C.HID_TEST is not None and C.HID_TEST not in TESTS:
        raise ValueError("HID_TEST invalide")

    controls = Inputs()
    keyboard = HIDKeyboard(runtime.interface) if runtime.interface else None

    # La LED est un confort : si son initialisation échoue, on continue.
    led = None
    try:
        from led import Led
        led = Led()
    except Exception as exc:
        print("LED desactivee :", exc)

    display.profile(manager.name, ticks_ms())
    print("Profil :", manager.name,
          "HID :", "initialise" if keyboard else "DESACTIVE")
    if runtime.hid_error:
        display.message("HID ERROR", "VOIR REPL")

    started = ticks_ms()
    armed = False          # False tant que la garde de démarrage n'est pas finie
    was_ready = False

    try:
        while True:
            now = ticks_ms()
            edges = controls.poll(now)

            # --- Fin de la garde de démarrage -----------------------
            if not armed and ticks_diff(now, started) >= C.BOOT_GUARD_MS:
                armed = True
                # Si tu tenais encore une touche, on l'ignore : il faudra
                # la relâcher avant qu'elle ne serve.
                controls.disarm_held()
                edges = []
                print("Entrees actives ; HID_TEST =", C.HID_TEST)

            if armed:
                pressed = [name for name, edge in edges if edge == 1]

                # --- 1. ESC : priorité absolue, avant tout le reste ---
                if "ESC" in pressed:
                    if keyboard:
                        keyboard.escape(now)
                        # On appelle tick() tout de suite : ainsi le paquet
                        # de relâchement part dans le même tour de boucle,
                        # sans attendre 2 ms de plus.
                        keyboard.tick(now)
                    if led:
                        led.flash(now)
                    print("ESC")
                else:
                    # --- 2. Changement de profil ---------------------
                    previous = "PREVIOUS" in pressed
                    following = "NEXT" in pressed
                    # Si les deux TTP sont touchés en même temps, on ne
                    # fait rien : on ne saurait pas dans quel sens aller.
                    if previous != following:
                        manager.move(1 if following else -1)
                        if keyboard:
                            # On annule la macro en cours : hors de question
                            # que la fin d'une commande de l'ancien profil
                            # continue de s'écrire après le changement.
                            keyboard.cancel()
                        display.profile(manager.name, now, True)
                        print("Profil :", manager.name)
                    else:
                        # --- 3. Les quatre touches de macro ----------
                        for i in range(4):
                            if "B" + str(i + 1) in pressed:
                                label, actions = PROFILES[manager.name][i]
                                if C.HID_TEST is not None:
                                    # En mode test, seul B1 agit, et il
                                    # déclenche la macro de test choisie.
                                    if i != 0:
                                        continue
                                    label, actions = C.HID_TEST, TESTS[C.HID_TEST]
                                print(manager.name, "B" + str(i + 1), label)
                                if keyboard:
                                    keyboard.submit(actions)
                                else:
                                    print("   (HID desactive : rien n'est tape)")

            # --- 4. Travaux de fond, tous non bloquants -------------
            if keyboard:
                keyboard.tick(now)
                ready = keyboard.ready()
                # Au moment précis où Windows ouvre le clavier, on ignore
                # ce qui est déjà maintenu : sinon un doigt encore posé
                # déclencherait une macro dès la connexion.
                if ready and not was_ready:
                    controls.disarm_held()
                was_ready = ready

            if led:
                try:
                    led.tick(now)
                except Exception as exc:
                    # Une panne de LED ne doit pas arrêter le clavier.
                    print("LED arretee :", exc)
                    try:
                        led.close()
                    except Exception:
                        pass
                    led = None

            display.tick(now)
            sleep_ms(C.LOOP_MS)

    finally:
        # Ce bloc s'exécute TOUJOURS : arrêt normal, Ctrl-C dans Thonny,
        # ou erreur imprévue. C'est là qu'on garantit qu'aucune touche ne
        # reste enfoncée côté Windows et que la LED est éteinte.
        if keyboard:
            keyboard.close()
        if led:
            led.close()


if __name__ == "__main__":
    run()
