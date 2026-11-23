# Audit des données pour l'app « comme sur le vrai banc »

Généré par `tools/audit_data.py` — ne pas éditer à la main. ✅ prêt · 🟡 partiel · ❌ manquant.

| Domaine | Élément | État | Détail |
|---|---|---|---|
| Plaque | géométrie des trous, blocs, rails coupés au W, 7 connecteurs, adresses | ✅ | adressage T/N/TOP unique, validé par 12 montages |
| Plaque | points encore « a_confirmer » dans board_wish106.yaml | 🟡 | 4 occurrence(s) : rangée 1 en bas, structure du bus haut, côté âme des BNC… |
| Comportement | hardware/behavior.yaml : paramètres (TL081, LED, résistances, TTL, GBF, oscillo, alim) | 🟡 | 24 vérifiés, 11 à vérifier, 15 à remplir (valeurs null) |
| Comportement | modèle SPICE complet du TL081 (offset, polarisation, sortie dépendant de la charge) | ❌ | seul le modèle comportemental à un pôle existe (tools/netlist.py) |
| Comportement | modèles numériques 74LS00 / 74LS74 (seuils, retards, sorties) | 🟡 | seuils et retards du 74LS74 lus dans le guide ; retards du 74LS00 manquants ; pas de moteur numérique |
| Comportement | multimètre (bande passante, impédance d'entrée) | ❌ | non photographié ni décrit |
| Instruments | scope : zones cliquables nécessaires | ✅ | 16 zones ; manquantes : aucune |
| Instruments | gbf : zones cliquables nécessaires | ✅ | 28 zones ; manquantes : aucune |
| Instruments | psu : zones cliquables nécessaires | ✅ | 18 zones ; manquantes : aucune |
| Instruments | oscillo : boutons de position verticale (voies 1 et 2), menus de voie (couplage, sonde), menu Trigger, touches de menu à droite de l'écran | ❌ | non cartographiés : il faut une photo de face nette et la liste des menus utilisés |
| Instruments | GBF : arbre des menus (Parameter, Setup → charge High Z, unités) | 🟡 | chemin High Z noté « à vérifier » dans tous les montages |
| Instruments | alimentation : écran, sélection de voie, saisie de tension et de limite | 🟡 | photo des ports et du clavier ; chemin des menus non décrit |
| Montages | 12 montages : câblage valide (validateur) | ✅ | 12 montages YAML |
| Montages | netlist extractible depuis le câblage | ✅ | 12/12 ; avec puce numérique non simulée : tp3-A2-seuils, tp3-A-nand, tp3-B-bascule-D, tp3-C-compteur |
| Montages | réglages d'appareils LISIBLES PAR LA MACHINE (amplitude, fréquence, V/div, tensions d'alim) | ❌ | aujourd'hui du texte libre dans « reglages » pour les 12 montages : il faut un bloc « settings: » structuré (voir docs/ARCHITECTURE_APP.md §5) |
| Montages | résultat attendu lisible par la machine (pour comparer à ce que fait l'élève) | 🟡 | TP1 et TP2 : predictions/*.yaml (27 cas) ; TP3 : aucun |
| Montages | valeurs de résistances dans la série E12 | 🟡 | 9,1 kΩ (non inverseur, association) et 20 kΩ ne sont pas E12 : vérifier les montages |
| Vérité terrain | photos d'écran d'oscilloscope (TP2) pour caler le modèle | 🟡 | 3 photos ; sans valeurs mesurées associées (circuit, réglages inconnus) |
| Vérité terrain | tes mesures de TP (Cr-cr, phases, Rint…) dans un fichier structuré | ❌ | elles existent seulement dans des .md (COMPTE_RENDU_PERSO_TP*.md) : créer mesures_reelles.yaml |
| Vérité terrain | tests de non-régression : moteur de l'app contre predict.py et check_netlist.py | 🟡 | check_netlist.py compare déjà 14 points (< 0,1 %) ; manque l'export JSON de référence |

**Bilan : 6 prêts, 9 partiels, 5 manquants.**
