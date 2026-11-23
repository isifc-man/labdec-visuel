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
