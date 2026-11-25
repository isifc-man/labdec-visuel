# Intégration des correctifs du collègue — tableau de vérification

Base : `isifc-man/labdec-visuel` @ `a58999f` (origin/main, aucun commit ni ticket depuis). Branche locale : `integration-correctifs`.

| # | Élément | Méthode | Résultat | Action |
|---|---|---|---|---|
| 1 | 3 patchs du collègue sur le GitHub actuel | `git am --3way` sur clone neuf | s'appliquent sans conflit | intégrés (3 commits) |
| 2 | Build `tools/build_app.py` | clone neuf | échec : `out/` absent | **corrigé** (mkdir) |
| 3 | Tests moteur (36) | `node tests/engine_test.js` | tous OK | — |
| 4 | Tests interface (54 + 7 nouveaux) | jsdom 24 | tous OK, aucune erreur JS | 7 tests ajoutés |
| 5 | Puces des 9 montages corrigés (TL081 ×6, 74LS00 ×2, 74LS74 ×2) | script d'audit : chaque broche → vrai trou `strip`, pas de trou partagé | 0 anomalie | — |
| 6 | Géométrie : dessin (`board.js`) vs électrique (`Engine.pinHole`) | lecture + comparaison des formules | identiques (j = broches 1..n/2 du haut vers le bas, a = le reste du bas vers le haut ; fente entre j et a) | — |
| 7 | Outil Puce à la main | sonde : clic 74LS00 rangée 3 / 6, TL081 rangée 2 | broches hors plaque, GND perdue, sans alerte | **corrigé** : calage dans la plaque + refus du chevauchement |
| 8 | HTML du collègue vs build intégré | comparaison des fonctions JS et des marqueurs | mêmes fonctions ; seule différence : extraits du sujet (retirés chez le collègue) | — |
| 9 | LED (outil, dessin, courant, clignotement) | tests moteur + interface « TP1 D » | OK | intégré |
| 10 | Correctifs « des autres étudiants » | `gh issue list` / PR sur le dépôt | **aucun ticket, aucune PR** | rien à reporter |
| 11 | Clic simple sur une prise (vrai Chrome 127.0.0.1) | état lu après chaque clic | 1er clic : outil « câble » + bout armé, 0 câble ; 2e clic : 1 câble `A` | comportement conforme, testé |
| 12 | Double-clic sur un câble posé (vrai Chrome, code d'origine) | `double_click` sur le câble A | **aucun effet** (impossible de déplacer sans la gomme) | **corrigé** (déplacement par double-clic) |
| 13 | Déplacement de câble (jsdom, 19 tests) | clic simple, double-clic, Échap, refus, BNC prise, gomme, changement de montage | tous OK | — |
| 14 | Déplacement de câble dans le vrai Chrome (après correction) | — | **non refait** : extension Chrome déconnectée en cours de route | à refaire |
