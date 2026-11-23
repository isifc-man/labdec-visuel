# Architecture de l'app « banc de TP à la maison »

Objectif : poser des composants sur la plaque Wish Board 106, câbler GBF / oscilloscope / alimentation, et **voir à l'écran de l'oscilloscope ce que le vrai banc afficherait**, pour réviser le TP d'électronique chez soi.
Document rédigé le 2026-11-06. Chaque affirmation est marquée **[vérifié]** (testé ou lu à la source) ou **[non vérifié]**.

---

## 1. Verdict

| Question | Réponse |
|---|---|
| Faisable ? | **Oui, pour TP1 et TP2 avec un bon niveau de fidélité ; TP3 demande un moteur numérique en plus.** |
| Le plus dur est-il déjà fait ? | Oui : le passage « trous posés sur la plaque → circuit électrique » existe et est **vérifié** (§3). |
| Existe-t-il déjà une app qui fait ça ? | **Non** : aucune app trouvée ne combine plaque ISIFC + GBF/oscillo/alim Keysight (§2). On réutilise un **moteur**, pas une app. |
| Risque principal | Le moteur de simulation navigateur n'a **pas pu être testé ici** (installation npm refusée par le système de permissions). Plan B prévu (§4.3). |
| Ce qui manque | 5 éléments ❌ et 9 🟡 : voir `AUDIT_DONNEES_APP.md` (généré par `tools/audit_data.py`). |

## 2. Ce qui existe déjà (recherche web du 2026-11-06)

| Projet | Ce que c'est | Pour ton cas |
|---|---|---|
| [EEcircuit / eecircuit-engine](https://github.com/eelab-dev/EEcircuit-engine) | ngspice compilé en WebAssembly, netlist SPICE en entrée ; npm `eecircuit-engine` 1.9.0, licence **MIT** (modifié le 2026-10-31) | **Moteur recommandé (plan A)**. API documentée : `new Simulation()`, `await sim.start()`, `sim.setNetList(txt)`, `await sim.runSim()`. |
| [CircuitJS1 (Falstad)](https://github.com/pfalstad/circuitjs1) | simulateur interactif dans le navigateur, **GPLv2**, intégrable en iframe | Schéma, pas plaque ; pas d'instruments Keysight ; la GPL contaminerait ton app si tu réutilises son code. Utile comme inspiration seulement. |
| [UCL Breadboard Simulator](https://www.homepages.ucl.ac.uk/~zcapbmk/breadboard/) | plaque virtuelle + oscillo + GBF + multimètre, analogique | Concept le plus proche ; téléchargement, pas de dépôt GitHub confirmé, pas ta plaque. |
| [BreadboardSim](https://github.com/daveshah1/BreadboardSim) | plaque virtuelle pour le lycée, **GPLv3**, Windows | Pas d'oscillo ni de GBF confirmés. |
| Chippy, louiseann/vbb | plaques / portes logiques | Logique seulement. |
| VISIR | laboratoire à distance avec vrais appareils | Aucune simulation : mesures réelles. |

**À propos d'eecircuit-engine, ce que son README ne dit PAS [non vérifié]** : forme exacte de l'objet résultat (tension en fonction du temps, données complexes en AC), exécution Node ou Web Worker, version de ngspice, disponibilité des modèles numériques XSPICE, disponibilité des fonctions `min` / `max` dans les sources comportementales, taille du paquet utile. Licence de ngspice lui-même : à vérifier (seul le wrapper est confirmé MIT).

## 3. Ce qui est déjà vérifié dans ce projet

`tools/netlist.py` transforme un montage YAML en netlist (nœuds = trous reliés par fil, rail, bus ; câbles BNC et bananes ; GBF 50 Ω ; entrées d'oscillo 1 MΩ ∥ 16 pF ; alim flottante). `tools/check_netlist.py` résout ce netlist (solveur linéaire MNA, numpy) et le compare à `tools/predict.py` :

| Montage | Points testés | Écart gain | Écart phase |
|---|---|---|---|
| Pont diviseur | 1 kHz, 1 MHz, 10 MHz | ≤ 0,09 % | 0,0° |
| Suiveur | 1 kHz, 1 MHz, 4 MHz | ≤ 0,00 % | 0,0° |
| Inverseur / non inverseur / association | 1 kHz et à leur fréquence de coupure | ≤ 0,02 % | 0,0° |
| Impédance interne, soustracteur | 1 kHz | ≤ 0,01 % | — |

**[vérifié]** : le câblage posé sur la plaque suffit à reconstruire le circuit, et deux calculs indépendants (formules ; netlist + MNA) concordent. Limite : ce test est **linéaire** ; la saturation, la vitesse de montée, la LED et le numérique ne sont pas dans ce test.

**Deux règles découvertes par le test** (le solveur linéaire seul ne les voit pas) : (1) puce **non alimentée** (V− oublié) → l'app doit afficher « AOP non alimenté » ; (2) **alimentation flottante** (douille ⏚ non reliée à la plaque) → avertissement. Les deux sont implémentées dans le prototype (`warnings`, `dc=True`).

## 4. Architecture

### 4.1 Couches

```
YAML (hardware, montages, predictions, behavior)
        │  build (export JSON)
        ▼
┌───────────────────────────── navigateur (hors ligne, PWA) ─────────────────────────────┐
│ UI plaque (SVG)   ──►  ÉTAT { pièces, fils, câbles, réglages d'appareils }               │
│  placer / câbler        │  (même format que les montages YAML)                           │
│                         ▼                                                                │
│               EXTRACTEUR DE NETLIST   (port TypeScript de render.validate + netlist.py)  │
│                         │  règles : alim, masse flottante, court-circuit, BNC 2 fils     │
│                         ▼                                                                │
│        MOTEUR  ── analogique : ngspice-WASM dans un Web Worker (plan A)                  │
│                │            ou solveur TypeScript maison (plan B)                        │
│                └─ numérique (TP3) : simulateur à événements, seuils + retards            │
│                         ▼                                                                │
│        MODÈLES D'APPAREILS : GBF · alim (CV/CC) · oscillo · multimètre                   │
│                         ▼                                                                │
│        ÉCRAN D'OSCILLO (Canvas) + faces avant cliquables (photos + zones)                │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 « Temps réel » : ce que ça veut dire ici
Un oscilloscope déclenché affiche une image **stable**. On ne diffuse donc pas un flux : à chaque changement (fil, composant, réglage) on **relance** une simulation sur une fenêtre de 10 × (temps/div) plus un temps d'établissement, puis on redessine. Les modes Run / Stop / Single et Auto / Normal s'implémentent sur cet état. Durée d'une simulation : **[non mesuré]** — premier critère du banc d'essai du §7 (objectif : sous 200 ms pour un montage TP2).

### 4.3 Plan A / Plan B
- **A. ngspice-WASM** : vrai solveur non linéaire (LED, saturation, vitesse de montée, numérique XSPICE si disponible). Dépend des points non vérifiés du §2.
- **B. Solveur TypeScript** : nous avons déjà le solveur linéaire (MNA) et le modèle de l'AOP (un pôle + vitesse de montée + saturation) dans `predict.py` ; il faut ajouter Newton pour la LED. Plus long à écrire, aucun risque de dépendance. Bascule si le banc d'essai du §7 échoue.

### 4.4 Modèles d'appareils (comportements à reproduire)
| Appareil | Comportements essentiels | Source |
|---|---|---|
| GBF | 50 Ω de sortie ; « High Z » = affichage à vide, « 50 Ω » = ×2 à vide ; offset ; Sync TTL 5 V ; sortie ON/OFF ; fronts non nuls | sujet TP1 ; `behavior.yaml` |
| Oscillo | 1 MΩ ∥ 16 pF ; 8 × 10 divisions ; V/div, temps/div, offset ; couplage ; déclenchement (source, front, niveau, Auto/Single) ; Auto Scale (voie 1 en haut, voie 2 en bas) ; mesures **Moy - PE, Fréq, Max, Cr-cr, Phase** ; curseurs | photos ; `behavior.yaml` ; **algorithme d'Auto Scale à reconstituer** |
| Alim | sorties flottantes ; limite de courant (passage en CC) ; trois voies | sujet TP2 annexe 1 |
| Multimètre | bande passante en AC, impédance d'entrée | **absent** |
| Câbles / fils | capacité de câble BNC (≈ 100 pF/m, hypothèse) ; fil = court-circuit | `behavior.yaml` |

### 4.5 Mode révision
- **Mode libre** : poser n'importe quoi, l'app simule et avertit (puce non alimentée, 0 V flottant, BNC câblé une seule fois, trou utilisé deux fois).
- **Mode leçon** : l'app charge un montage `montages/*.yaml` comme cible et compare les **nœuds** (jeux de bornes reliées, indépendamment des trous choisis) : « il manque le fil entre la broche 6 et la résistance R2 ». Les règles existent déjà dans `render.validate`.
- **Mode séance 30 min** : la page `seance_30min.html` devient une liste cochable avec chronomètre et contrôle automatique.

## 5. Formats de données

**Existant et suffisant** : `hardware/board_wish106.yaml`, `hardware/components.yaml`, `hardware/instruments/*.yaml` (photos + zones), `montages/*/*.yaml` (qui **sont déjà le format de sauvegarde de l'app**, sans la clé `noeuds`), `predictions/*.yaml`, `hardware/behavior.yaml` (créé aujourd'hui).

**À ajouter** (aujourd'hui du texte libre dans `reglages`, donc illisible par un moteur) :

```yaml
# dans chaque montage
instruments:
  gbf:
    settings: {forme: sine, vpp: 5.0, freq_hz: 1000, offset_v: 0.0, charge: HighZ, sortie: on}
  scope:
    settings:
      ch1: {actif: true, v_div: 1.0, offset_v: 0.0, couplage: DC, sonde: 1}
      ch2: {actif: true, v_div: 1.0, offset_v: 0.0, couplage: DC, sonde: 1}
      temps_div_s: 0.0002
      declenchement: {source: 1, front: montant, niveau_v: 0.0, mode: auto}
      mesures: [moy_pe_1, freq_1, max_1, max_2]
  psu:
    settings: {ch1: {v: 1.0, i_max: 0.1, on: true}, ch2: {v: 15.0, i_max: 0.1, on: true}, ch3: {v: 15.0, i_max: 0.1, on: true}}
```
```yaml
# mesures_reelles.yaml  (tes vraies mesures de TP : sert à CALER le modèle)
- {id: tp2-B1-2026-11-0x, montage: tp2-B1-inverseur, gbf: {vpp: 0.4, freq_hz: 1000}, mesures: {cr_cr_1: 0.4, cr_cr_2: 7.9, phase_2_1: 180.0}, photo: scope_tp2_a.jpg}
```
Aucune valeur n'est inventée : les `null` de `behavior.yaml` se remplissent dans la fiche constructeur ou par mesure.

## 6. Fidélité : ce qui sera réaliste et ce qui ne le sera pas

| Effet | Prévu ? | Remarque |
|---|---|---|
| Charge du GBF (50 Ω), de l'oscillo (1 MΩ ∥ 16 pF), du câble | ✅ | déjà dans le prototype |
| Saturation, vitesse de montée, bande passante de l'AOP | ✅ | paramètres de la fiche TI |
| Mauvais câblage (alim oubliée, masse flottante, BNC à un seul fil) | ✅ | règles du §3 |
| LED (seuil, courant) | ✅ | paramètres à confirmer (couleur) |
| Logique 74LS (seuils, retards) | 🟡 | retards 74LS74 connus ; 74LS00 à remplir |
| Auto Scale et menus exacts de l'oscillo | 🟡 | à reconstituer d'après photos et usage |
| Bruit, quantification 8 bits, sonde non compensée, boucle de masse | ❌ | optionnel : ajouter après calage |
| Tolérances réelles des résistances (±5 %), dispersion des puces | 🟡 | tirage aléatoire en option |
| Pics et ondulations de ta photo B | ❌ | cause non identifiée ; ne pas simuler sans explication |

L'app donnera donc **les mêmes ordres de grandeur et les mêmes artefacts**, pas les mêmes bruits ni les mêmes défauts d'un exemplaire précis.

## 7. Feuille de route, avec critère de réussite pour chaque étape

| Étape | Contenu | Critère de réussite |
|---|---|---|
| **M0 — fait** | Données, validateur, netlist, comparaison à `predict.py` | 14 points ≤ 0,1 % (§3) ✔ |
| **M1 — banc d'essai moteur** | Installer `eecircuit-engine` dans un dossier jetable ; y faire tourner le netlist de l'inverseur (`tools/netlist.py: to_spice`) ; lire la forme du résultat | résultat conforme à `check_netlist` ; temps < 200 ms ; fonctions `min`/`max` acceptées ; sinon bascule plan B |
| **M2 — parité transitoire** | Rejouer les 27 cas de `predictions/*.yaml` avec le moteur | Cr-cr, phase, Moy - PE à ±2 % de `predict.py` ; saturation et trapèze visibles |
| **M3 — oscilloscope** | Port TypeScript de `scope_svg` ; déclenchement, Auto Scale, mesures, curseurs | les 3 photos A/B/C reproduites (test déjà prêt : `out/scope_tests.html`) |
| **M4 — plaque interactive** | Placer composants et fils sur la plaque ; netlist en direct ; faces avant cliquables | un montage TP2 câblé à la souris donne le même écran que la page de prédiction |
| **M5 — mode leçon / séance** | Comparaison aux montages cibles, chrono, score | les 8 erreurs volontaires du validateur sont signalées en clair |
| **M6 — TP3 numérique** | Simulateur à événements + LED ; chronogrammes Q0/Q1 | `tp3-C-compteur` : Q0 = f/2, Q1 = f/4, retard Q0→Q1 visible à 10 ns/div |
| **M7 — calage** | Remplir `mesures_reelles.yaml` ; ajuster les paramètres `a_verifier` | écarts modèle/mesures documentés |

Hébergement : site statique (GitHub Pages ou fichiers locaux) + PWA hors ligne ; aucun serveur ; dépôt privé. Pile suggérée : TypeScript, Vite, Web Worker, tests Vitest ; les JSON de référence sont exportés par le build Python.

## 8. Ce dont j'ai besoin de toi

1. **Autorisation du banc d'essai M1** : `npm install eecircuit-engine` dans un dossier jetable (refusé par le système de permissions pendant cette séance ; je ne l'ai pas contourné).
2. **Photos** : face avant nette de l'oscilloscope + liste des menus que tu utilises ; l'alimentation (comment tu règles tension et limite) ; **le multimètre** (modèle).
3. **Tes mesures de TP** dans un fichier structuré (ou dis-moi lesquelles reprendre des `COMPTE_RENDU_PERSO_TP*.md`).
4. **Appareil cible** : ordinateur, tablette ou téléphone ? La pose de fils à la souris ne se conçoit pas pareil au doigt.
5. Les points `a_confirmer` du banc (T sur le GBF, douilles ±15 V, côté âme des BNC, bus du haut).
