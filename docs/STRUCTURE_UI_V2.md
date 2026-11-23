# Structure de l'UI v2 — LABDEC_VISUEL

Rédigé le 2026-11-21, avant toute ligne de code de l'interface. Source : lecture de `build_interactive.py`, du JS généré (`out/labdec_interactif.html`), des 12 montages YAML, de `hardware/instruments/*.yaml` et des photos `assets/photos/`.
Chaque point est marqué **[vérifié]** (lu dans les fichiers ou sur les photos) ou **[à calibrer]**.

---

## 1. Ce que fait l'app actuelle, point par point

### Ce qui marche et qu'on garde [vérifié]
| Élément | Où | Pourquoi on le garde |
|---|---|---|
| Géométrie de la plaque Wish 106, adressage `T1b62`, `N2-1u-40`, `TOP-L1-3` | `hardware/board_wish106.yaml`, `board.js` extrait | validé par les 12 montages |
| Validation du câblage (nœuds, BNC âme + blindage, alim, masse) | `render.py`, union-find JS | 80/80 connexions attendues retrouvées (TASKS 2026-11-13) |
| Extraction de netlist + solveur AC | `netlist.py`, `check_netlist.py` | 14 points ≤ 0,1 % contre `predict.py` |
| Les 12 montages YAML (fils, résistances, puces, câbles d'appareils, nœuds) | `montages/tp*/` | c'est déjà le format de sauvegarde |
| Zones cliquables des photos (GBF 28, oscillo 16, alim 18) | `hardware/instruments/*.yaml` | les câbles se posent dessus |

### Ce qui ne marche pas dans l'app interactive [vérifié dans le JS généré]
| # | Défaut | Preuve |
|---|---|---|
| 1 | **L'écran ne dépend pas du montage posé.** Gains écrits en dur par identifiant : inverseur −20, non-inverseur 10,1, association −202, soustracteur 1, pont 0,1. Changer R2 ne change rien. | `evaluateCircuit()` : `vsGain = isPowered ? -20.0 : 0.0` |
| 2 | **Signal affiché sans câblage.** Le pont diviseur donne `vsGain = 0.1` même sur plaque vide ; pour les TL081, seule l'alimentation est testée, pas le chemin du signal. | idem |
| 3 | **Tout est sinus.** Un carré ou un triangle du GBF sort en sinus sur la voie 2. | boucle de rendu : `Math.sin(...)` pour `v2` |
| 4 | **TP3 non simulé.** Les 4 montages tombent sur `vsGain = 1.0`. | branche `else` |
| 5 | **Une seule puce.** Poser une puce remplace `placedChips`. TP2-C (2 × TL081) et TP3-C impossibles à la souris. | `state.placedChips = [{ ref: "U1", ...}]` |
| 6 | **Forme : l'app n'utilise pas les photos.** Les appareils sont des formulaires HTML (listes déroulantes, champs numériques) et un canvas dessiné à la main. Plus rien ne ressemble au vrai banc ni ne dit où brancher les câbles. | `view-split` : `<select>`, `<input>` |
| 7 | **Montage choisi dans un `<select>` plat**, sans TP, sans sujet, sans questions, sans corrigé. | `#select-montage` |
| 8 | Détails : unité fausse (`ch1_vdiv × 1000` + « mV/ » même à 1 V), fanions 1 et 2 dessinés au même endroit, `confirm()` bloquant sur « Vider », 1 300 lignes de JS dans un f-string Python (`{{ }}`). | lecture du code |

Conclusion : **la plaque et le validateur sont bons ; ce qui est faux, c'est tout ce qui est « appareils + écran ».** Le moteur correct existe déjà en Python mais n'a jamais été branché sur l'écran.

---

## 2. Comment les montages s'enchaînent [vérifié : clés `precedent` des YAML]

```
TP1   B1 pont diviseur        C1 impédance interne        D1 LED
TP2   A suiveur → B1 inverseur → B2 non inverseur → C association
                       └──────→ D soustracteur
TP3   A NAND → A2 seuils → B bascule D → C compteur
```
Chaque montage dit « pars du précédent, retire tel fil, ajoute tel autre » (`etapes_montage`). L'UI doit donc proposer **« Partir du montage précédent »** en plus de « Partir de zéro », et afficher la différence (fils à retirer / à ajouter).

Câbles d'appareils par montage [vérifié] : TP1 et TP2 ont les mêmes câbles A–C (GBF → BNC1, T vers voie 1, voie 2 ← BNC2). TP2 ajoute D–G (alim : +15 V → VC, −15 V → VB, 0 V → MASSE, strap voie 2 − / voie 3 +). TP3-C utilise `gbf.sync_out` et l'alim voie 1 (5 V). Ces câbles ne se posent pas à la main : ils font partie du montage.

---

## 3. Organisation de l'interface

```
┌ LABDEC_VISUEL ──────────────────────────────────────────────────────────────────────────────┐
│ ☰  TP2 · B1. Inverseur            [Sujet] [Questions] [Composants] [Corrigé]     ⎌  ⟲ zéro  │
├───────────────┬─────────────────────────────────────────────┬───────────────────────────────┤
│ ▾ TP1         │   PLAQUE Wish 106                           │  SUJET  (objectif, schéma)    │
│    B1 Pont ÷10│   (fils, résistances, puces)                │  ─────────────────────────    │
│    C1 Rint GBF│                                             │  QUESTIONS (à prédire)        │
│    D1 LED     │   ┌──────────┐ ┌──────────┐ ┌──────────┐    │   1. Quel Vpp pour Vs ?       │
│ ▾ TP2         │   │   GBF    │ │  OSCILLO │ │  ALIM    │    │      [voir ce que l'écran     │
│    A Suiveur  │   │ (photo)  │ │ (photo)  │ │ (photo)  │    │       affiche]                │
│  ▸ B1 Inverseur◂  │ écran    │ │ écran    │ │ écran    │    │  COMPOSANTS                   │
│    B2 Non inv.│   │ calculé  │ │ calculé  │ │ calculé  │    │   R1 [820Ω][1k][1,2k]…        │
│    C Association  └──────────┘ └──────────┘ └──────────┘    │   R2 [10k][20k]… U1 TL081     │
│    D Soustract.│   câbles : points d'accroche sur les photos │  CORRIGÉ pas à pas            │
│ ▾ TP3         │                                             │   étape 1 [indice] [poser]    │
│    A NAND     │                                             │  ÉTAT : ✓ nœuds 5/6  ⚠ alim   │
│    …          │                                             │                               │
│ ○ Mode libre  │                                             │                               │
└───────────────┴─────────────────────────────────────────────┴───────────────────────────────┘
```

**Menu de gauche** : un arbre TP → montages, dans l'ordre de la chaîne du §2, avec une pastille d'avancement (○ à faire, ◐ en cours, ● validé = tous les nœuds reliés et écran conforme). Titres = champ `titre` des YAML. « Mode libre » en bas.

**Sélection d'un montage** → le visuel LABDEC s'ouvre vide (« de zéro ») avec : la plaque, les trois appareils, les câbles d'appareils déjà posés, et les réglages de départ lus dans le YAML (ex. B1 : sinus 0,4 Vpp, 1 kHz, High Z).

**Panneau de droite** (4 onglets) :
1. **Sujet** : objectif, pannes classiques du YAML.
2. **Questions** : les `a_predire` de `predictions/tp*.yaml` (27 cas). Réponse affichée à la demande, **calculée par le moteur** (pas recopiée).
3. **Composants** : pour chaque référence (R1, R2, U1…), la valeur correcte et ses voisines E12. Le choix arme l'outil de pose. Note déjà connue : 9,1 kΩ n'est pas E12 (→ 8,2 kΩ + 820 Ω, gain 10,02).
4. **Corrigé** : les `fils` du YAML, un par étape, **en indirect** : d'abord le rôle (« broche 3 à la masse »), puis [indice : les trous], puis [poser]. « Tout poser » en dernier recours.

---

## 4. Les écrans : on n'ajoute pas 2 écrans, on remplace ce qui est dans les photos

Décision retenue : **abandonner les formulaires HTML et les canvas dessinés ; utiliser les photos des appareils comme faces avant**, garder leurs zones de câblage et de boutons, et **remplacer uniquement la zone d'écran de chaque photo par un canvas calculé.**

| Appareil | Photo | Garde (zones existantes) | Remplace |
|---|---|---|---|
| Oscilloscope | `scope_tp2_b.jpg` 1600×1200 | `bnc_ch1`, `bnc_ch2`, `btn_autoscale`, `btn_run_stop`, `knob_*`, `btn_meas`, `btn_cursors` | zone `ecran` : grille, traces, mesures Cr-cr / Phase / Moy-PE, curseurs |
| GBF | `gbf_ports.jpg` 2048×1536 | `out1`, `sync_out`, `btn_*`, `keypad_*`, `softkey_*`, `btn_ch1_onoff` | zone écran (à gauche de la photo) : forme d'onde, fréquence, amplitude, charge, OFF/ON |
| Alim | `psu_ports.jpg` | `ch1_plus … ch3_moins` | zone écran : tensions, limites de courant, CV/CC |

Rectangles d'écran **[à calibrer]** : le YAML ne donne qu'un point (`ecran: [450, 450]`). Lecture à l'œil des photos : écran de l'oscillo ≈ x 170–745 (sans le menu bleu à droite, jusqu'à ≈ 880 avec), y 258–655 ; écran du GBF ≈ x 0–595, y 125–805 (coupé à gauche par la photo). À mesurer précisément avant de coder (étape 1 du §6).

**Que montre chaque écran ?** Il ne dépend plus de gains codés : il est le résultat de la simulation du câblage réellement posé.
- **Oscillo** : voie 1 = nœud relié au port `scope.ch1`, voie 2 = `scope.ch2`. Les deux sont calculés (§5).
- **GBF** : affiche ce que l'élève a réglé via les vrais boutons (Waveform, Parameter, pavé, Setup → High Z). Ce réglage alimente la source du moteur.
- **Alim** : affiche les tensions réglées ; avertit si le 0 V est flottant.

Les boutons des photos deviennent les vraies commandes (cliquer sur Waveform ouvre les softkeys dessinées dans la zone écran). C'est plus long à faire que des formulaires ; première version : zones cliquables → petit panneau flottant avec les valeurs, la zone écran se met à jour.

---

## 5. Le moteur derrière les écrans

Pipeline : `câblage posé + câbles d'appareils → nœuds → netlist → solveur AC (MNA complexe) → Vs/Ve, déphasage, point continu → formes d'onde (saturation, vitesse de montée, passe-bas) → pixels de l'écran`.
Port JS de `netlist.py` ; paramètres de `hardware/behavior.yaml` (TL081 : 4 MHz et 13 V/µs vérifiés ; saturation 12,5 V à vérifier).

**Écran attendu = même moteur appliqué au câblage corrigé du montage.** Pas de code par montage : on compare la simulation de l'élève à celle du YAML solution (gain à ±2 %, phase à ±3°). C'est la version générale du souhait « soit son code, soit le code de ce que l'on attend à l'écran ».

**Limites déclarées, jamais masquées** :
- TP3 (74LS00, 74LS74) et LED : pas de moteur numérique ni de diode. L'écran affiche « non simulé » plutôt qu'un faux signal. Étape M6 de `ARCHITECTURE_APP.md`.
- Pas de bruit, de quantification 8 bits ni de tolérances de résistances.
- Écarts connus modèle/mesures à trancher : fc du non-inverseur 396 → 230 kHz mesuré, slew 13 → 5,5 V/µs noté, seuils NAND 1,2–1,5 V mesurés contre 1,7 / 0,9 V de la fiche (TASKS.md).

---

## 6. Ordre de construction

| Étape | Contenu | Critère de réussite |
|---|---|---|
| 1 | Calibrer les rectangles d'écran sur les 3 photos (ajouter `ecran_rect` dans les YAML d'appareils) | le rectangle recouvre l'écran à ±5 px sur la photo |
| 2 | `engine.js` : port de `netlist.py`, testé sous Node | inverseur −20, non-inverseur ≈ 10,1, suiveur 1, pont 0,1, et mêmes écarts que `check_netlist.py` |
| 3 | `lessons/tpN/*.yaml` : sujet, questions, composants, étapes, réglages de départ (tirés des YAML existants) | 12 fiches, aucune valeur inventée |
| 4 | Squelette de l'UI : arbre à gauche, plaque au centre, panneau de droite | on change de montage sans recharger, état remis à zéro |
| 5 | Faces avant sur photos + canvas d'écran + câbles d'appareils | un TP2 câblé à la souris donne le même écran que `predictions_tp2.html` |
| 6 | Corrigé en indirect, comparaison à l'écran attendu, pastilles d'avancement | les erreurs volontaires du validateur sont signalées en clair |

Déjà fait (additif, dans `app/`) : `css/base.css`, `partials/board_svg.html`, `js/board.js`, `js/checks.js`, `js/interactions.js`, `js/scope_cursors.js`, extraits tels quels de l'ancienne app. `engine.js` n'a pas pu être écrit (disque plein) : étape 2.

## 7. Ce qu'on voit, écran par écran (ASCII — version 1, à ajuster)

Tout ce qui est marqué `▓▓` est **calculé par le moteur** ; le reste est la photo réelle.

### 7.1 Page complète (état : TP2 · B1 sélectionné, plaque vide)
```
┌─ LABDEC_VISUEL ───────────────────────────────────────────────────────────────────────────────────┐
│ TP2 · B1. Inverseur (Av = −20)                         [⟲ de zéro] [⇤ depuis A] [⎌ annuler]       │
├──────────────────┬─────────────────────────────────────────────────────────┬──────────────────────┤
│ MONTAGES         │ PLAQUE Wish Board 106  (SVG interactif)                 │ ▸Sujet ▸Questions    │
│                  │ ┌─────────────────────────────────────────────────────┐ │ ▸Composants ▸Corrigé │
│ ▾ TP1            │ │ [BNC1]  [BNC2]  [VB] [VC] [⏚]      bus haut ═══════ │ │ ──────────────────── │
│   ○ B1 Pont ÷10  │ │ N1 N2 │ T1 f g h i j ╎ a b c d e │ N3 N4 │ T2 …     │ │ (contenu de l'onglet)│
│   ○ C1 Rint GBF  │ │ rails │ fils, R, puce posés ici  │ rails │          │ │                      │
│   ○ D1 LED       │ └─────────────────────────────────────────────────────┘ │                      │
│ ▾ TP2            │                                                         │                      │
│   ● A Suiveur    │ ┌─ GBF (photo) ───┐ ┌─ OSCILLO (photo) ─┐ ┌─ ALIM (photo)┐│                      │
│  ◐▶B1 Inverseur  │ │ ▓ écran ▓       │ │ ▓▓ écran ▓▓       │ │ ▓ écran ▓    ││                      │
│   ○ B2 Non inv.  │ │ boutons         │ │ boutons, molettes │ │ boutons      ││ ──────────────────── │
│   ○ C Assoc.     │ │ ◉Out1 ◉Sync     │ │ ◉CH1      ◉CH2    │ │ ◉1+ 1− 2+ 2−…││ ÉTAT                 │
│   ○ D Soustract. │ └─────────────────┘ └───────────────────┘ └──────────────┘│ ✓ 0/6 nœuds          │
│ ▾ TP3 …          │   câbles d'appareils = points ◉ déjà reliés (A–G)         │ ⚠ AOP non alimenté   │
│ ○ Mode libre     │                                                         │                      │
└──────────────────┴─────────────────────────────────────────────────────────┴──────────────────────┘
 ○ à faire   ◐ en cours   ● validé (nœuds OK + écran conforme)
```

### 7.2 Oscilloscope : photo réelle + écran calculé (lu sur `scope_tp2_b.jpg` et `scope_screen_empty.jpg`)
```
┌─ KEYSIGHT DSOX1202A · 70 MHz 2 GSa/s ───────────────────────────────────────────┐
│ ┌─ ÉCRAN (▓ calculé) ─────────────────────────────────────┬─ menu bleu ───────┐ │ [Run/Stop]  [Single]
│ │ 1 2.00V/  2 2.00V/        0.0s   200µs/   Auto  ⚡1 0V   │ Acquisition       │ │ [Auto Scale]
│ │ ┌───────────────────────────────────────────────────┐   │  Normal 2GSa/s    │ │ [Default Setup]
│ │ │                     ·  ·  ·                        │   │ Voies             │ │ (○ Horizontal)
│ │ │   ╱╲        ╱╲        grille 10 × 8                │   │  DC 1.00:1 (CH1)  │ │ [Meas] [Cursors]
│ │ │  ╱  ╲      ╱  ╲   ← voie 1 jaune (Ve)             │   │  DC 1.00:1 (CH2)  │ │ (○ Vertical) [1] [2]
│ │ │ ╱────╲────╱────╲─  ← voie 2 verte (Vs)             │   │ Math / Réf        │ │ (○ Trigger) [Menu]
│ │ └───────────────────────────────────────────────────┘   │                   │ │
│ │ Moy-PE(1) │ Fréq(1)  │ Max(1)   │ Max(2)   │ 10:01 PM   │                   │ │
│ │  0.00 V   │ 1.000kHz │  200 mV  │  4.00 V  │            │                   │ │
│ └─────────────────────────────────────────────────────────┴───────────────────┘ │
│        ◉ CH1 (BNC jaune)       ◉ CH2 (BNC verte)       ◉ Ext Trig               │
└──────────────────────────────────────────────────────────────────────────────────┘
```
Réalité lue sur les photos : bandeau du haut « voie 1 V/div · voie 2 V/div · 0.0s · temps/div · Auto · ⚡ voie niveau », barre du bas par défaut **Moy-PE(1), Fréq(1), Max(1), Max(2)**, panneau bleu à droite avec Acquisition / Voies / Math / Réf. Si on appuie sur Meas on ajoute Cr-cr et Phase (photo B : Cr-cr(1), Cr-cr(2), Phase(2→2), Phase(2→1)). Sans signal : « Aucun signal ».

### 7.3 Générateur (lu sur `gbf_ports.jpg`)
```
┌─ Keysight EDU33211A · 20 MHz ───────────────────────────────────────────────┐
│ ┌─ ÉCRAN (▓) ──────────────────┬─ softkeys ─┐  [Waveform][Parameter][Units]  │
│ │ OFF            KEYSIGHT      │ Sine       │◀ (6 touches grises)            │
│ │ ┌────────────┐ Waveform      │ Square     │  [Modulate][Sweep][Burst]      │
│ │ │   ╱╲       │               │ Ramp       │  7 8 9   ( molette )           │
│ │ │ ─╱──╲──╱─  │               │ Pulse      │  4 5 6                         │
│ │ └────────────┘               │ Arb        │  1 2 3          Channel 1      │
│ │ 1.000 kHz · 400 mVpp · High Z│ MORE 1/2   │  0 . +/-       [Setup] [On/Off]│
│ └──────────────────────────────┴────────────┘                                │
│  ◉Cal   ◉Ext Trig   ◉Sync/Trigger Out         ◉ OUT 1 (50 Ω) + adaptateur T  │
└──────────────────────────────────────────────────────────────────────────────┘
```
`On/Off` jaune = sortie active. « High Z » se règle par Setup (chemin à vérifier sur ton appareil).

### 7.4 Alimentation (lue sur `psu_ports.jpg`)
```
┌─ Keysight EDU36311A · 6V/5A, 30V/1A, 30V/1A ─────────────────────────────────┐
│ ┌─ ÉCRAN (▓) ───────────┐ softkeys          [Meter View][Tracking]  7 8 9     │
│ │ CH1  0.000 V  0.000 A │ Source Settings ▾ ( ▲ ◀ Select ▶ ▼ )   4 5 6     │
│ │ CH2 15.000 V  0.0xx A │ Output Settings ▾                       1 2 3     │
│ │ CH3 15.000 V  0.0xx A │ Store/Recall ▾    [All On/Off]  [Enter] 0 . ⌫     │
│ │ ⚠ 0 V flottant ?      │ Utilities ▾       (V) (I)  boutons On: ⬤ ⬤ ⬤      │
│ └───────────────────────┘                                                     │
│ ⏚vert   ┃ 1  +◉ −◉ ┃ 2  +◉ −◉ ┃ 3  +◉ −◉ ┃   (jaune / vert / bleu)            │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 7.5 Panneau de droite, les 4 onglets (état B1)
```
SUJET                         QUESTIONS                       COMPOSANTS                    CORRIGÉ
┌─────────────────────┐       ┌───────────────────────────┐   ┌─────────────────────────┐   ┌──────────────────────────┐
│ B1. Inverseur       │       │ 1 Quel Vpp pour Vs ?      │   │ R1  ( ) 820Ω (●) 1kΩ    │   │ Étape 1/11  ○ fait ○     │
│ Ve 0,4 Vpp 1 kHz →  │       │   [voir l'écran attendu]  │   │     ( ) 1,2kΩ           │   │ « Ve : âme BNC1 → R1 »   │
│ Vs 8 Vpp opposition │       │ 2 Vs en phase avec Ve ?   │   │ R2  ( ) 10kΩ (●) 20kΩ   │   │ [indice : BNC1.core→T1g53]│
│ de phase, non saturé│       │   [voir…]                 │   │     ( ) 2×10kΩ série    │   │ [poser]                  │
│ Pannes classiques : │       │ 3 À 5 Vpp, que se passe-t-│   │ U1  TL081 (8 broches)   │   │ …                        │
│ • Vs écrêtée ±13 V  │       │   il ? [voir…]            │   │ [armer l'outil de pose] │   │ [tout poser — dernier    │
│ • Vs ≈ 0 : broche 3 │       └───────────────────────────┘   └─────────────────────────┘   │  recours]                │
└─────────────────────┘                                                                      └──────────────────────────┘
```

### 7.6 Parcours d'un montage
```
clic « B1 Inverseur » (menu gauche)
   → plaque vide + câbles d'appareils A–G posés + réglages de départ lus dans le YAML
   → Sujet / Questions : l'élève prédit
   → Composants : choisit R1, R2, U1 → pose sur la plaque (clic trou, clic trou)
   → écrans (GBF, oscillo, alim) se mettent à jour à chaque pose
   → État : nœuds ✓ / ⚠ ; pastille ○ → ◐ → ●
   → Corrigé (si bloqué) : indice → pose → tout poser
```

---

## 8. Questions ouvertes
1. **Appareil cible** : ordinateur uniquement, ou aussi tablette ? Les photos et la pose de fils au doigt ne se conçoivent pas pareil.
2. **Multimètre** (TP1-B2) : pas de photo, donc pas de face avant. À ajouter plus tard ou à ignorer ?
3. Les points `a_confirmer` du banc (T sur la sortie du GBF, côté âme des BNC, sens a–e / f–j) restent à vérifier sur le vrai banc.
