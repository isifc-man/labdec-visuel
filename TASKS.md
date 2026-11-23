# TASKS — LABDEC_VISUEL
Créé : 2026-11-06 | Mis à jour : 2026-11-06 (soir)

## Avancement : 13/19 — 68 %

## Fait
- [x] Structure de dossiers + photos rangées
- [x] hardware : plaque Wish 106 (lettres a–e / f–j, rangées, rails coupés au W), GBF, oscillo, alim, brochages TL081 / 74LS00 / 74LS74
- [x] Générateur + validateur (build.py → render.py, montage_page.py, bench.py) : adresses, trous uniques, BNC âme+blindage, douilles alimentées câblées, puces DIP, nœuds distincts
- [x] Test de fidélité du rendu d'écran (3 photos TP2)
- [x] Moteur de prédiction d'écran (predict.py) : GBF 50 Ω, oscillo 1 MΩ, TL081 (GBP 4 MHz, 13 V/µs, ±12,5 V), RC, LED
- [x] Barre du bas de l'écran = ta config : Moy - PE(1), Fréq(1), Max(1), Max(2)
- [x] Prédictions TP2 (5 circuits, 16 cas avec artefacts) et TP1 (4 circuits, 11 cas), plaque câblée à côté de chaque circuit
- [x] Page « Séance 30 minutes » : 27 cas × 1 min + 12 montages avec « ce qu'il faut changer depuis le précédent »
- [x] Montages TP1 : B1 pont diviseur, C1 impédance interne (3 fils), D1 LED
- [x] Montages TP2 : A suiveur, B1 inverseur, B2 non inverseur, C association, D soustracteur
- [x] Montages TP3 : A NAND+LED, A2 seuils, B bascule D, C compteur gauche
- [x] Prédictions TP2 alignées sur les valeurs des montages présents sur le disque (R2 = 20 kΩ, 9,1 kΩ ; Ve = 0,4 / 1 / 0,04 Vpp)

- [x] Architecture de l'app « banc à la maison » : docs/ARCHITECTURE_APP.md ; audit des données : docs/AUDIT_DONNEES_APP.md (tools/audit_data.py) ; paramètres de comportement : hardware/behavior.yaml
- [x] Extraction de netlist depuis la plaque + solveur AC (tools/netlist.py, tools/check_netlist.py) : 14 points ≤ 0,1 % contre predict.py
- [x] Simulateur interactif de câblage sur Wish Board 106 (`out/labdec_interactif.html` + `tools/build_interactive.py`) : pointer/poser câbles et résistances, inspecteur de trou, checklist en temps réel et validation électrique des 12 montages type.

- [x] 2026-11-13 — Page de validation complète pour la relecture par l'enseignante : `out/validation_TP1_TP2_TP3.html` (+ PDF), générée par `tools/validation_complete.py` (13 parties, 63 blocs de validation, export des remarques). Nouveaux modules : `tools/ttl_ports.py` (brochages TL081 / 74LS00 / 74LS74, schémas NAND, bascule D, compteur), `tools/exemple_bloc.py` (exemple d'un bloc).

- [x] 2026-11-13 — Audit des 12 montages : 80/80 connexions attendues trouvées (`SPEC` dans `tools/validation_complete.py`) + `check_netlist.py` OK. Incohérences corrigées dans la page : soustracteur (plaque = V1 GBF / V2 alim ; `predictions/tp2.yaml` suppose l'inverse, NON modifié), compteur (sondes plaque : voie 1 = CLK, voie 2 = Q0), noms R3/R4 de l'étage 2.
- [x] 2026-11-13 — Dossier à envoyer : `A_ENVOYER_PROF/` (HTML autonome, PDF 103 p., LISEZ_MOI.txt, ZIP).

## À faire
- [ ] Aligner `predictions/tp2.yaml` (scénario « v1_continu » du soustracteur) sur le câblage de la plaque (V1 = GBF, V2 = alim) : la page de validation le corrige déjà localement
- [ ] Relire la page de validation (écarts signalés : fc du non-inverseur 396 → 230 kHz mesuré, slew rate 13 → 5,5 V/µs noté, saturation 12,5 / 13,5 V, seuils NAND mesurés 1,2–1,5 V contre 1,7 / 0,9 V de la fiche) et trancher les valeurs du modèle
- [ ] Versions à envoyer : fichier HTML autonome (déjà intégré : images en base64) et/ou PDF (14 Mo, à alléger si besoin)
- [ ] M1 banc d'essai moteur : `npm install eecircuit-engine` dans un dossier jetable (refusé par le système de permissions, en attente de ton accord) ; valider le modèle SPICE du TL081 (non exécuté)
- [ ] Ajouter un bloc `settings:` structuré (GBF, oscillo, alim) à chaque montage ; créer mesures_reelles.yaml
- [ ] Photos : face avant nette de l'oscillo + menus utilisés, alim (réglage tension/limite), multimètre
- [ ] Confirmer sur le banc : T sur la sortie du GBF, côté âme des BNC, sens a–e/f–j, rangée 1 en bas, bus haut, douilles +15 V / −15 V / 0 V (VC / VB / ⏚)
- [ ] Résistances : 9,1 kΩ (non inverseur, association) n'est PAS E12 → 8,2 kΩ + 820 Ω (gain 10,02) ; 20 kΩ → 2 × 10 kΩ
- [ ] Prédictions d'écran TP3 (74LS00 / 74LS74 : seuils, retard de propagation, chronogrammes Q0/Q1)
- [ ] Compteur droit (synchrone, bonus TP3) ; TP1-B2 (multimètre) en page séparée
- [ ] Comparer les prédictions à TES mesures (Cr-cr, phase, Moy - PE) et corriger le modèle si écart
- [ ] Plus tard : application qui réagit comme le vrai banc selon ce qui est câblé (le validateur et le moteur de prédiction en sont la base)

## Blocages
- Aucun bloquant.

## Décisions clés
- YAML = source de vérité ; HTML/SVG générés ; Markdown = lecture humaine.
- Photos réelles pour les appareils (pastilles numérotées), SVG généré pour la plaque et les écrans.
- Python : /usr/bin/python3 (3.9, PyYAML présent) ; le python3 par défaut n'a pas PyYAML et pip y est bloqué. Entrée unique : tools/build.py.
- Le 2026-11-06 à 17:01, les montages TP2 ont été réécrits et les montages TP3 ajoutés par un autre processus de session (disposition de la plaque différente de ma première version : puce rangée 50, rails N1/N2). État courant conservé.
