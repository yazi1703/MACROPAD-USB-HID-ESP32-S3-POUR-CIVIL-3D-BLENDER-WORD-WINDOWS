# -*- coding: utf-8 -*-
"""
injecter_page.py - Recopie tools/page_config.html dans les deux serveurs.

La meme page de configuration est servie a deux endroits :
  * device/portal.py  -> par le WiFi du macropad
  * pc/macropad_auto.py -> par le cable USB depuis le PC

Pour qu'elles ne divergent jamais, la source unique est
tools/page_config.html et ce script l'injecte dans les deux fichiers,
entre les marqueurs PAGE = \"\"\" et \"\"\".

    python3 tools/injecter_page.py
"""

import os

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(RACINE, "tools", "page_config.html")
CIBLES = [os.path.join(RACINE, "device", "portal.py"),
          os.path.join(RACINE, "pc", "macropad_auto.py")]


def main():
    with open(SOURCE, encoding="utf-8") as fichier:
        page = fichier.read().rstrip("\n")

    if '"""' in page:
        raise SystemExit("La page ne doit pas contenir de triple guillemet.")

    for cible in CIBLES:
        with open(cible, encoding="utf-8") as fichier:
            source = fichier.read()
        debut = source.index('PAGE = """')
        fin = source.index('"""', debut + 10)
        neuf = source[:debut] + 'PAGE = """' + page + '\n' + source[fin:]
        with open(cible, "w", encoding="utf-8") as fichier:
            fichier.write(neuf)
        print("page injectee dans", os.path.relpath(cible, RACINE))


if __name__ == "__main__":
    main()
