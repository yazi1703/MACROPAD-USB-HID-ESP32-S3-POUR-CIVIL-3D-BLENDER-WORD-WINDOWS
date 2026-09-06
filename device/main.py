# -*- coding: utf-8 -*-
"""
main.py - Le chef d'orchestre. Lancé automatiquement après boot.py.

=====================================================================
LES TROIS MODES
=====================================================================
boot.py a déjà décidé lequel s'applique, selon ce que tu maintenais
pendant le RESET :

  SAFE MODE   (B1) : on affiche un écran d'alerte et on rend la main au
                     REPL. Aucun clavier n'existe.
  MODE CONFIG (B2) : on allume le WiFi et on sert la page web de
                     configuration. Aucun clavier n'existe non plus.
  NORMAL           : le macropad fait son travail.

=====================================================================
LE PRINCIPE DU MODE NORMAL : UNE SEULE BOUCLE, JAMAIS D'ATTENTE
=====================================================================
Tout tient dans une boucle qui tourne environ 500 fois par seconde. À
chaque tour on fait un tout petit peu de chaque travail :

    1. lire les entrées
    2. traiter ESC en priorité
    3. traiter les profils et les macros
    4. envoyer AU PLUS un paquet clavier
    5. mettre à jour la LED
    6. envoyer AU PLUS une page d'écran
    7. dormir 2 ms, et on recommence

C'est une boucle coopérative : chaque tâche prend un petit morceau de
temps puis rend la main volontairement. Écrire une commande de seize
caractères (400 ms) n'empêche donc jamais le bouton ESC de répondre.

L'ordre n'est pas anodin : ESC est traité en tout premier.

=====================================================================
D'OÙ VIENNENT LES MACROS
=====================================================================
De `profils.json` s'il existe (créé par la page web), sinon des valeurs
d'usine de `profiles.py`. Si le fichier est corrompu, on repart sur les
valeurs d'usine en le signalant : le macropad ne peut pas devenir
inutilisable à cause d'un fichier de configuration.
"""

from time import ticks_ms, ticks_diff, sleep_ms
import config as C
import runtime
import store
from inputs import Inputs
from profiles import ProfileManager, TESTS
from display import Display
from hid_keyboard import HIDKeyboard
from layouts import compile_actions
from link import Link, EVT_PROFIL, EVT_DOCUMENT, EVT_RECHARGER

NB_TOUCHES = len(C.BUTTON_PINS)


# =====================================================================
# MODE CONFIG : WiFi + page web
# =====================================================================
def mode_config(display):
    """Allume le point d'accès et sert la page de configuration.

    Aucun clavier n'a été créé par boot.py : ce mode ne peut rien taper.
    On en sort par un RESET normal.
    """
    from portal import demarrer_ap, arreter_ap, Portail

    print("=" * 46)
    print(" MODE CONFIGURATION")
    print("=" * 46)

    # Une LED allumée fixe, différente de la respiration habituelle :
    # d'un coup d'œil tu sais que le macropad n'est pas un clavier.
    led = None
    try:
        from led import Led
        led = Led()
        led.set_level(C.LED_MAX)
    except Exception as exc:
        print("LED desactivee :", exc)

    portail = None
    try:
        ssid, cle, adresse = demarrer_ap()
        display.config_screen(ssid, cle, adresse)
        display.flush_startup()
        print("1. Connecte-toi au reseau WiFi :", ssid)
        print("2. Cle :", cle)
        print("3. Ouvre http://%s dans un navigateur" % adresse)
        print("4. Modifie tes macros, enregistre, puis fais un RESET.")

        portail = Portail(NB_TOUCHES)
        portail.ouvrir()
        while True:
            portail.service()          # rend la main au bout de 0,25 s
    except KeyboardInterrupt:
        print("Mode configuration interrompu.")
    except Exception as exc:
        print("MODE CONFIG en echec :", exc)
        display.message("CONFIG KO", str(exc)[:16])
        display.flush_startup()
    finally:
        if portail:
            portail.fermer()
        arreter_ap()
        if led:
            led.close()


# =====================================================================
# MODE NORMAL
# =====================================================================
def run():
    display = Display()

    # --- SAFE MODE : on n'exécute rien, on rend la main au REPL --------
    if runtime.safe_mode:
        display.message("SAFE MODE", "HID DISABLED", "", "Boutons lisibles",
                        "Aucune frappe")
        display.flush_startup()
        print("SAFE MODE : le clavier n'existe pas.")
        print("REPL disponible. Diagnostics : import diag; diag.run()")
        return

    # --- MODE CONFIG : WiFi + page web ---------------------------------
    if runtime.config_mode:
        mode_config(display)
        return

    # --- Chargement des macros -----------------------------------------
    profils, ordre, titres, origine = store.charger(NB_TOUCHES)
    print("Macros chargees depuis :", origine)

    manager = ProfileManager(ordre, C.DEFAULT_PROFILE, profils, NB_TOUCHES)

    # Vérification de TOUTES les macros avant la moindre frappe. Une macro
    # impossible à taper doit échouer ici, pas au milieu d'une commande.
    for nom in ordre:
        for label, actions in profils[nom]:
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

    # Liaison avec le PC : detection automatique du logiciel actif et
    # configuration a distance. Facultative : sans le script cote PC, le
    # macropad fonctionne exactement comme avant.
    lien = Link(NB_TOUCHES) if C.LINK_ENABLED else None
    verrouille = False          # True = l'auto ne peut plus changer de profil
    dernier_auto = None         # instant du dernier message du PC

    def afficher(splash):
        display.profile(titres.get(manager.name, manager.name),
                        manager.macros, ticks_ms(),
                        manager.index, len(ordre), splash)

    def recharger_profils():
        """Relit profils.json et applique la nouvelle configuration.

        Appele quand le PC vient d'enregistrer des macros : les changements
        prennent effet immediatement, sans RESET.
        """
        nonlocal manager, titres, ordre
        try:
            neufs, ordre_neuf, titres_neufs, origine_neuve = store.charger(NB_TOUCHES)
            nouveau = ProfileManager(ordre_neuf, manager.name, neufs, NB_TOUCHES)
        except Exception as exc:
            print("[main] configuration refusee, on garde l'ancienne :", exc)
            return
        manager, titres, ordre = nouveau, titres_neufs, ordre_neuf
        afficher(False)
        print("Macros rechargees depuis :", origine_neuve)

    afficher(False)
    print("Profil :", manager.name,
          "HID :", "initialise" if keyboard else "DESACTIVE")
    if runtime.hid_error:
        display.message("HID ERROR", "VOIR REPL")

    demarre = ticks_ms()
    arme = False               # False tant que la garde de démarrage dure
    etait_pret = False
    etat_affiche = None
    dernier_controle = demarre

    try:
        while True:
            now = ticks_ms()
            fronts = controls.poll(now)

            # --- 0. Ce que dit le PC ---------------------------------
            if lien:
                for genre, valeur in lien.service():
                    if genre == EVT_PROFIL:
                        dernier_auto = now
                        # Le verrou te rend la main : si tu l'as active,
                        # le PC ne peut plus imposer de profil.
                        if (not verrouille and valeur in manager.order
                                and valeur != manager.name):
                            manager.index = manager.order.index(valeur)
                            if keyboard:
                                keyboard.cancel()
                            afficher(True)
                            print("Profil (auto) :", manager.name)
                    elif genre == EVT_DOCUMENT:
                        dernier_auto = now
                        display.set_document(valeur)
                    elif genre == EVT_RECHARGER:
                        recharger_profils()

            # --- Fin de la garde de démarrage -----------------------
            if not arme and ticks_diff(now, demarre) >= C.BOOT_GUARD_MS:
                arme = True
                # Si tu tenais encore une touche, on l'ignore : il faudra
                # la relâcher avant qu'elle ne serve.
                controls.disarm_held()
                fronts = []
                print("Entrees actives ; HID_TEST =", C.HID_TEST)

            if arme:
                appuyes = [nom for nom, front in fronts if front == 1]

                # --- 1. ESC : priorité absolue, avant tout le reste ---
                if "ESC" in appuyes:
                    if keyboard:
                        keyboard.escape(now)
                        # tick() tout de suite : le paquet part dans le
                        # même tour de boucle, sans attendre 2 ms de plus.
                        keyboard.tick(now)
                    if led:
                        led.flash(now)
                    print("ESC")
                else:
                    # --- 2. Changement de profil ---------------------
                    precedent = "PREVIOUS" in appuyes
                    suivant = "NEXT" in appuyes
                    # Les deux TTP touchés EN MEME TEMPS : on bascule le
                    # verrou. Profil verrouillé = le PC ne peut plus le
                    # changer tout seul, tu gardes la main.
                    if ((precedent or suivant)
                            and controls.items["PREVIOUS"].active()
                            and controls.items["NEXT"].active()):
                        verrouille = not verrouille
                        print("Verrouillage du profil :",
                              "ACTIF" if verrouille else "inactif")
                        afficher(False)
                    elif precedent != suivant:
                        manager.move(1 if suivant else -1)
                        if keyboard:
                            # On annule la macro en cours : hors de question
                            # que la fin d'une commande de l'ancien profil
                            # continue de s'écrire après le changement.
                            keyboard.cancel()
                        afficher(True)
                        print("Profil :", manager.name)
                    else:
                        # --- 3. Les touches de macro -----------------
                        for index in range(NB_TOUCHES):
                            if "B" + str(index + 1) not in appuyes:
                                continue
                            label, actions = manager.macros[index]
                            if C.HID_TEST is not None:
                                # En mode test, seul B1 agit.
                                if index != 0:
                                    continue
                                label, actions = C.HID_TEST, TESTS[C.HID_TEST]
                            print(manager.name, "B" + str(index + 1), label)
                            if not actions:
                                print("   (touche inactive)")
                            elif keyboard:
                                keyboard.submit(actions)
                            else:
                                print("   (HID desactive : rien n'est tape)")

            # --- 4. Travaux de fond, tous non bloquants -------------
            if keyboard:
                keyboard.tick(now)
                pret = keyboard.ready()
                # Au moment précis où Windows ouvre le clavier, on ignore
                # ce qui est déjà maintenu : sinon un doigt encore posé
                # déclencherait une macro dès la connexion.
                if pret and not etait_pret:
                    controls.disarm_held()
                etait_pret = pret

            # Petit indicateur en haut à droite de l'écran, rafraîchi
            # seulement quand il change (un redessin coûte 8 tours).
            if ticks_diff(now, dernier_controle) >= 250:
                dernier_controle = now
                auto = (dernier_auto is not None
                        and ticks_diff(now, dernier_auto) < C.AUTO_TIMEOUT_MS)
                if verrouille:
                    etat = "LOCK"          # tu as verrouillé le profil
                elif keyboard is None:
                    etat = "OFF"
                elif keyboard.fault:
                    etat = "ERR"
                elif not keyboard.ready():
                    etat = "..."
                elif auto:
                    etat = "AUTO"          # le PC pilote les profils
                else:
                    etat = "HID"
                if etat != etat_affiche:
                    etat_affiche = etat
                    display.set_etat(etat)

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
