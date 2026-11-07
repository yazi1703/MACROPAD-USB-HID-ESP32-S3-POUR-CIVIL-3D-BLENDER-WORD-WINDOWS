# Skills de design installés

Ces skills sont chargés automatiquement par Claude Code dans ce dépôt.
Ils ont été copiés depuis leurs dépôts d'origine le 2026-11-07, après relecture.

| Skill | Source (commit) | Licence | Popularité au 2026-11-07 |
|---|---|---|---|
| `frontend-design` | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/frontend-design) (`2c5958ecac7c`) | Apache-2.0 | Skill de design le plus installé : ~1,09 M installations sur skills.sh, n°2 du classement général |
| `web-design-guidelines` | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines) (`1a2c79d4e6c4`) | non précisée | ~834 000 installations sur skills.sh |
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (`b7d5353e0130`) | MIT | Dépôt de skill de design le plus étoilé : ~146 000 étoiles GitHub |
| `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (`687bc381bc90`) | Apache-2.0 | ~105 000 étoiles, mis à jour quotidiennement |
| `unslop` | [heydamir/unslop](https://github.com/heydamir/unslop) (`a6f121eee5f2`) | CC-BY-4.0 (créditer Damir Sokolovsky) | En forte hausse : créé le 2026-10-29, ~11 000 étoiles en 9 jours |

Sources de popularité : [LinklyAI/best-skills](https://github.com/LinklyAI/best-skills), qui agrège skills.sh et d'autres plateformes, et la recherche GitHub.

## À savoir

- `web-design-guidelines` télécharge ses règles à chaque audit depuis
  `raw.githubusercontent.com/vercel-labs/web-interface-guidelines`.
- `impeccable` télécharge au premier usage un exécutable depuis les releases GitHub
  de pbakaus/impeccable, vérifié avec `scripts/engine-checksums.txt`. Son hook
  de détection ne s'active que sur demande (`/impeccable hooks on`).
- `unslop` utilise Chrome et ffmpeg en local, uniquement pour les captures et la vidéo optionnelle.
- `ui-ux-pro-max` travaille hors ligne : un script Python cherche dans des fichiers CSV locaux.

## Modifications locales

- `ui-ux-pro-max/SKILL.md` : `${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/` est remplacé
  par `.claude/skills/ui-ux-pro-max/`. C'est le chemin documenté par l'auteur pour une
  installation dans un projet ; la variable n'existe que pour une installation en plugin.
  Le dossier `scripts/tests` n'a pas été copié.
- Les fichiers `LICENSE` et `NOTICE.md` des dépôts d'origine sont copiés dans les dossiers
  qui ne les contenaient pas.

## Écartés volontairement

- `taste-skill` (Leonxlnx, ~111 000 étoiles) : 40 Mo et 1 600 fichiers, trop lourd pour ce dépôt.
- `hallmark` (Nutlope, ~50 000 étoiles) : installe des hooks de lint sur chaque modification.
- `ui-taste`, `design-mobile-apps`, `uizze-ui` : plus d'un million d'installations annoncées,
  mais score de confiance de 0,2 et dépôts quasi vides (moins de 100 étoiles). Les chiffres
  semblent gonflés.
- Les skills `ai-image-generation` / `ai-video-generation` publiés sous 7 noms différents
  (skills-shell, 101-skills, magentosh…) : mêmes skills et compteurs qui montent ensemble,
  ce qui ressemble à des copies faites pour le classement.
