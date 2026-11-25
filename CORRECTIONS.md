# Journal des corrections

Une ligne par correction demandée (prof, camarade, relecture). Voir `docs/MODIFIER_APRES_VERIF.md` pour savoir quel fichier ouvrir.

| Date | Qui | Fichier modifié | Avant → Après | Pourquoi / source |
|---|---|---|---|---|
| 2026-11-22 | — | (exemple) `montages/tp2/B2_non_inverseur.yaml` | R2 = 9,1 kΩ → 8,2 kΩ + 820 Ω en série | 9,1 kΩ n'est pas dans la série E12 imposée par le sujet |
| 2026-11-23 | relecture | `app/js/engine.js` | solveur alternatif linéaire + écrêtage à la sonde → simulation temporelle (AOP par étage, alim CC, LED, 74LS00/74LS74) | audit : TP3 et LED non simulés, alim sans limite de courant, court-circuit = « matrice singulière » |
| 2026-11-23 | relecture | `app/js/scope.js` | mesures sur 900 points de l'écran → sur l'enregistrement ; tracé min/max | « Fréq(1) : Aucun signal » à 2 périodes ; 1 MHz affiché comme 10 kHz (repliement) ; phase = théorie au lieu de la courbe |
| 2026-11-23 | relecture | `app/js/checks.js` | contrôles codés en dur (TOP_L_1, U1.4, trous du corrigé) → bornes + appariement par valeur | fausses alertes si la masse est sur un autre bus ; montage juste mais décalé refusé |
| 2026-11-23 | relecture | `montages/tp3/A2_seuils.yaml` | VT+ ≈ 1,7 V / VT− ≈ 0,9 V → basculement ≈ 1,3 V, pas d'hystérésis | 1,7/0,9 V correspond à un trigger de Schmitt, pas au 74LS00 (fiche : VIL ≤ 0,8 V, VIH ≥ 2 V) |
| 2026-11-23 | relecture | `montages/tp3/A_nand.yaml` | « Y ≈ 1,0 V avec LED » → ≈ 3,2 V | avec 1,0 V la LED ne pourrait pas s'allumer |
| 2026-11-23 | relecture | `app/js/lesson.js` | appareils allumés au chargement → réglés mais éteints | sujet TP2 : « faites vérifier l'alimentation avant d'appuyer sur on » |
| 2026-11-23 | relecture | `app/js/engine.js` | Sync active seulement si la sortie est ON → Sync indépendante (menu Trigger, ON par défaut) | manuel EDU33210 : Sync activée par défaut, réglée dans [Trigger] ; désactivée elle reste à l'état bas |
| 2026-11-23 | ajout | `app/js/dmm.js`, `train.js`, `docs.js`, `predictions/tp3_logique.yaml` | multimètre, TP4 blanc, pannes, documentation des appareils, questions TP3 | demandes de l'utilisateur ; manque relevé à l'audit (TP1 B, TP3) |
| 2026-11-24 | intégration | `app/js/interactions.js` | outil Puce : la rangée cliquée devenait la broche 1 sans contrôle → calée dans la plaque (rangée ≥ n/2) et refus si la puce chevauche une autre | un 74LS00 cliqué rangée 6 avait sa masse (broche 7) sur un trou inexistant, sans alerte ; deux puces pouvaient partager les mêmes trous |
| 2026-11-24 | intégration | `tools/build_app.py` | plante dans un clone neuf (`out/` absent) → crée `out/` | reproduit en clonant le dépôt |
| 2026-11-24 | intégration | `tests/ui_smoke_test.js` | +7 tests de pose de puce (calage, GND/broche 8 de part et d'autre de la fente, chevauchement refusé, bord haut) | non-régression de la correction ci-dessus |
| 2026-11-24 | intégration | `app/js/cables.js` | un câble posé ne pouvait se déplacer qu'à la gomme (puis tout recâbler) → **double-clic sur le câble** : le bout le plus proche se décroche, l'autre reste armé, un clic sur la nouvelle prise rebranche (même lettre, même couleur) ; Échap ou pose refusée = câble remis ; ignoré avec la gomme | constaté dans Chrome : double-clic sans effet. La couche des câbles laisse passer les clics (sinon elle masque les prises) : le câble visé est trouvé par calcul de distance à la courbe |
| 2026-11-24 | intégration | `tests/ui_smoke_test.js` | +19 tests : clic simple = aucun câble, 2e clic = un câble, double-clic (vide / câble / près de chaque bout), déplacement, Échap, prise incompatible, BNC déjà prise, gomme, changement de montage en cours de déplacement | non-régression |
