# LABDEC_VISUEL

Pages de câblage générées depuis des fichiers YAML (plaque Wish Board 106, GBF/oscillo/alim Keysight).

## Utiliser
```
cd LABDEC_VISUEL
/usr/bin/python3 tools/build.py         # valide les montages + calcule les prédictions + génère le simulateur interactif -> out/*.html
open out/labdec_interactif.html         # BANC INTERACTIF : pointer, câbler sur la plaque Wish 106 et valider en direct
open out/index.html                     # portail général
```
App « banc à la maison » : lis `docs/ARCHITECTURE_APP.md` ; simulateur interactif : `out/labdec_interactif.html`.
Séance rapide : `out/seance_30min.html` (27 cas × 1 min + montages à câbler).
Pages principales : `out/predictions_tp2.html` (artefacts de l'AOP), `out/predictions_tp1.html`, `out/tp1-B1-pont-diviseur.html` (câblage complet).

## Prédire avant de regarder
Chaque scénario affiche d'abord les réglages et une question « à prédire » ; l'écran calculé est caché dans « Voir ce que l'oscilloscope affiche ».
Les courbes sont CALCULÉES (tools/predict.py) : GBF 50 Ω de sortie, oscillo 1 MΩ, TL081 (GBP 4 MHz, 13 V/µs, ±12,5 V), RC. Les hypothèses sont en tête de chaque page et modifiables dans `predictions/tp*.yaml`.
`/usr/bin/python3` (3.9) a PyYAML. Le `python3` par défaut n'en a pas.

## Où modifier quoi
| Je veux changer… | Fichier |
|---|---|
| un fil, une résistance, un réglage d'appareil d'un montage | `montages/tpN/<montage>.yaml` |
| la géométrie de la plaque, les connecteurs | `hardware/board_wish106.yaml` |
| un bouton / une prise sur une photo d'appareil | `hardware/instruments/*.yaml` (coordonnées en pixels) |
| la fidélité du rendu d'un écran d'oscillo | `tests/scope_tp2_*.yaml` |

Ne jamais éditer `out/*.html` à la main.

## Adresses
- `T1b62` : bloc 1, lettre b (bande de droite a–e ; la bande de gauche est f–j), rangée 62. Les 5 trous d'une rangée du même côté de la fente sont reliés.
- `N2-1u-40` : rail 2, colonne 1, moitié haute, position 40 (le rail est coupé au « W », entre 32 et 33).
- `TOP-L1-3` : bus du haut, côté gauche, ligne 1, position 3 (masse).
- `BNC1.core` / `BNC1.shield` : âme / blindage. Un BNC se câble toujours DEUX fois.

## Ce que le validateur contrôle
adresses valides · aucun trou utilisé deux fois · BNC câblé âme ET blindage · résistance non court-circuitée · nœuds exigés bien reliés · nœuds distincts jamais en contact · blindages à la masse commune.

## Statuts
Tout point marqué « à confirmer » n'est pas vérifié sur ton banc (T sur la sortie du GBF, sens a–e/f–j (lu par l'utilisateur : f–j à gauche, a–e à droite), rangée 1 en bas, structure du bus haut).
