# -*- coding: utf-8 -*-
"""
main.py - Le chef d'orchestre. Lance automatiquement apres boot.py.

=====================================================================
LES TROIS MODES
=====================================================================
boot.py a deja decide lequel s'applique, selon ce que tu maintenais
pendant le RESET :

  SAFE MODE   (B1) : ecran d'alerte, retour au REPL. Aucun clavier.
  MODE CONFIG (B2) : WiFi + page web de configuration. Aucun clavier.
  NORMAL           : le macropad fait son travail.

=====================================================================
LE PRINCIPE DU MODE NORMAL : UNE SEULE BOUCLE, JAMAIS D'ATTENTE
=====================================================================
Tout tient dans une boucle qui tourne environ 500 fois par seconde. A
chaque tour on fait un tout petit peu de chaque travail :

    0. ecouter le PC (profil automatique, configuration)
    1. lire les entrees
    2. traiter ESC en priorite
    3. profils, verrouillage, gestes des touches
    4. envoyer AU PLUS un paquet clavier
    5. mettre a jour la LED
    6. envoyer AU PLUS une page d'ecran
    7. dormir 2 ms, et on recommence

C'est une boucle cooperative : chaque tache prend un petit morceau de
temps puis rend la main volontairement. Ecrire une commande de seize
caracteres (400 ms) n'empeche donc jamais le bouton ESC de repondre.

=====================================================================
TROIS GESTES PAR TOUCHE
=====================================================================
Appui court, appui long, double appui : voir gestures.py. Une touche sans
macro double part instantanement au relachement ; on ne paie le delai
d'attente que la ou on s'en sert.
"""

from time import ticks_ms, ticks_diff, sleep_ms
import config as C
import runtime
import store
from inputs import Inputs
from profiles import ProfileManager, TESTS, COURT
from gestures import Gestes
from stats import Stats
from display import Display
from hid_keyboard import HIDKeyboard
from layouts import compile_actions
from link import Link, EVT_PROFIL, EVT_DOCUMENT, EVT_RECHARGER

NB_TOUCHES = len(C.BUTTON_PINS)


# =====================================================================
# MODE CONFIG : WiFi + page web
# =====================================================================
def mode_config(display):
    """Allume le point d'acces et sert la page de configuration.

    Aucun clavier n'a ete cree par boot.py : ce mode ne peut rien taper.
    On en sort par un RESET normal.
    """
    from portal import demarrer_ap, arreter_ap, Portail

    print("=" * 46)
    print(" MODE CONFIGURATION")
    print("=" * 46)

    # LED allumee fixe, differente de la respiration habituelle : d'un
    # coup d'oeil tu sais que le macropad n'est pas un clavier.
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

        portail = Portail(NB_TOUCHES, Stats(NB_TOUCHES))
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

    if runtime.safe_mode:
        display.message("SAFE MODE", "HID DISABLED", "", "Boutons lisibles",
                        "Aucune frappe")
        display.flush_startup()
        print("SAFE MODE : le clavier n'existe pas.")
        print("REPL disponible. Diagnostics : import diag; diag.run()")
        return

    if runtime.config_mode:
        mode_config(display)
        return

    # --- Chargement de la configuration --------------------------------
    profils, ordre, titres, apps, repli, origine = store.charger(NB_TOUCHES)
    print("Macros chargees depuis :", origine)

    manager = ProfileManager(ordre, C.DEFAULT_PROFILE, profils, NB_TOUCHES)

    # Verification de TOUTES les macros avant la moindre frappe. Une macro
    # impossible a taper doit echouer ici, pas au milieu d'une commande.
    for nom in ordre:
        for label, gestes_touche in profils[nom]:
            for actions in (gestes_touche or {}).values():
                compile_actions(actions, C.KEYBOARD_LAYOUT)
    if C.HID_TEST is not None and C.HID_TEST not in TESTS:
        raise ValueError("HID_TEST invalide")

    controls = Inputs()
    keyboard = HIDKeyboard(runtime.interface) if runtime.interface else None
    stats = Stats(NB_TOUCHES)
    gestes = Gestes(NB_TOUCHES, C.GESTE_LONG_MS, C.GESTE_DOUBLE_MS)
    gestes.configurer(manager.macros)

    led = None
    try:
        from led import Led
        led = Led()
    except Exception as exc:
        print("LED desactivee :", exc)

    lien = Link(NB_TOUCHES, stats=stats) if C.LINK_ENABLED else None
    verrouille = False          # True = l'auto ne peut plus changer de profil
    dernier_auto = None

    def afficher(splash):
        display.profile(titres.get(manager.name, manager.name),
                        manager.macros, ticks_ms(),
                        manager.index, len(ordre), splash)
        gestes.configurer(manager.macros)

    def recharger_profils():
        """Relit profils.json et applique la nouvelle configuration.

        Appele quand une page web vient d'enregistrer : les changements
        prennent effet immediatement, sans RESET.
        """
        nonlocal manager, titres, ordre
        try:
            neufs, ordre_neuf, titres_neufs, _apps, _repli, origine_neuve = \
                store.charger(NB_TOUCHES)
            nouveau = ProfileManager(ordre_neuf, manager.name, neufs, NB_TOUCHES)
        except Exception as exc:
            print("[main] configuration refusee, on garde l'ancienne :", exc)
            return
        manager, titres, ordre = nouveau, titres_neufs, ordre_neuf
        afficher(False)
        print("Macros rechargees depuis :", origine_neuve)

    def declencher(index, geste):
        """Execute la macro correspondant a un geste sur une touche."""
        label, gestes_touche = manager.macros[index]
        actions = (gestes_touche or {}).get(geste)
        if C.HID_TEST is not None:
            # En mode test, seul l'appui court sur B1 agit.
            if index != 0 or geste != COURT:
                return
            label, actions = C.HID_TEST, TESTS[C.HID_TEST]

        print("%s B%d %s %s" % (manager.name, index + 1, geste, label or "-"))
        display.surligner(index, ticks_ms())
        if not actions:
            print("   (aucune macro sur ce geste)")
            return
        stats.compter(manager.name, index)
        if keyboard:
            keyboard.submit(actions)
        else:
            print("   (HID desactive : rien n'est tape)")

    afficher(False)
    print("Profil :", manager.name,
          "HID :", "initialise" if keyboard else "DESACTIVE")
    if runtime.hid_error:
        display.message("HID ERROR", "VOIR REPL")

    demarre = ticks_ms()
    arme = False
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

            # --- Fin de la garde de demarrage ------------------------
            if not arme and ticks_diff(now, demarre) >= C.BOOT_GUARD_MS:
                arme = True
                controls.disarm_held()
                fronts = []
                print("Entrees actives ; HID_TEST =", C.HID_TEST)

            if arme:
                for nom, front in fronts:
                    display.reveiller(now)      # tout appui reveille l'ecran

                    # --- 1. ESC : priorite absolue --------------------
                    if nom == "ESC":
                        if front == 1:
                            if keyboard:
                                keyboard.escape(now)
                                # tick() tout de suite : le paquet part dans
                                # le meme tour de boucle.
                                keyboard.tick(now)
                            if led:
                                led.flash(now)
                            print("ESC")
                        continue

                    # --- 2. Profils et verrouillage -------------------
                    if nom in ("PREVIOUS", "NEXT"):
                        if front != 1:
                            continue
                        # Les deux TTP touches EN MEME TEMPS : on bascule le
                        # verrou. Profil verrouille = le PC ne peut plus le
                        # changer tout seul, tu gardes la main.
                        if (controls.items["PREVIOUS"].active()
                                and controls.items["NEXT"].active()):
                            verrouille = not verrouille
                            print("Verrouillage du profil :",
                                  "ACTIF" if verrouille else "inactif")
                            afficher(False)
                        else:
                            manager.move(1 if nom == "NEXT" else -1)
                            if keyboard:
                                # Hors de question que la fin d'une commande
                                # de l'ancien profil continue de s'ecrire.
                                keyboard.cancel()
                            afficher(True)
                            print("Profil :", manager.name)
                        continue

                    # --- 3. Les touches de macro ----------------------
                    if nom.startswith("B"):
                        index = int(nom[1:]) - 1
                        if front == 1:
                            geste = gestes.appui(index, now)
                        else:
                            geste = gestes.relachement(index, now)
                        if geste:
                            declencher(index, geste)

                # Appuis longs et doubles appuis arrives a echeance.
                for index, geste in gestes.service(now):
                    declencher(index, geste)

            # --- 4. Travaux de fond, tous non bloquants -------------
            if keyboard:
                keyboard.tick(now)
                pret = keyboard.ready()
                if pret and not etait_pret:
                    controls.disarm_held()
                etait_pret = pret

            if ticks_diff(now, dernier_controle) >= 250:
                dernier_controle = now
                auto = (dernier_auto is not None
                        and ticks_diff(now, dernier_auto) < C.AUTO_TIMEOUT_MS)
                if verrouille:
                    etat = "LOCK"          # tu as verrouille le profil
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
                    print("LED arretee :", exc)
                    try:
                        led.close()
                    except Exception:
                        pass
                    led = None

            display.tick(now)
            sleep_ms(C.LOOP_MS)

    finally:
        # Ce bloc s'execute TOUJOURS : arret normal, Ctrl-C, ou erreur.
        # C'est la qu'on garantit qu'aucune touche ne reste enfoncee cote
        # Windows, que la LED est eteinte et que les compteurs sont sauves.
        if keyboard:
            keyboard.close()
        if led:
            led.close()
        stats.enregistrer()


if __name__ == "__main__":
    run()
