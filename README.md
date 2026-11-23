# LABDEC_VISUEL — banc d'électronique virtuel

Simulateur de TP d'électronique (plaque d'essai, générateur, oscilloscope, alimentation) : on câble comme sur la vraie plaque et **les écrans des appareils se calculent à partir du câblage**. Tout tourne dans le navigateur, hors ligne, sans serveur.

> Projet étudiant indépendant. Non affilié à Keysight ni à l'établissement. Les noms d'appareils ne servent qu'à décrire le matériel simulé.

## Utiliser
**Lien direct : https://isifc-man.github.io/labdec-visuel/**  (rien à installer ; la page est un fichier HTML unique : enregistrée sur l'ordinateur, elle s'ouvre hors ligne)

Ouvrir le lien de l'application (GitHub Pages) ou, en local : `python tools/build_app.py` puis ouvrir `out/labdec_app.html`. Prérequis : Python 3 + `pip install pyyaml`, Node.js pour les tests.

## Ce qui est simulé (et ce qui ne l'est pas)
Le moteur (`app/js/engine.js`) fait une **simulation temporelle** du circuit câblé (méthode nodale, intégration implicite, Newton pour les diodes), en régime établi, puis l'oscilloscope lit cet enregistrement.
- **Appareils** : GBF 50 Ω (sinus, carré, triangle, offset, High Z / 50 Ω, sortie Sync 0–5 V) ; oscilloscope 1 MΩ ∥ 16 pF + câble ; alimentation 3 voies flottantes **avec limite de courant (CV/CC)**, court-circuit compris.
- **TL081** : GBW 4 MHz, 13 V/µs, saturation **par étage** (montages en cascade), sortie 50 Ω, courant de repos ; non alimenté ou alimenté à l'envers signalé.
- **LED** (TP1 D, TP3) : diode exponentielle (paramètres de `hardware/behavior.yaml`), allumée sur la plaque, clignote en temps réel sous ~25 Hz ; surintensité signalée.
- **74LS00 / 74LS74** (TP3) : seuil 1,3 V, entrée en l'air = 1, sorties ≈ 3,5 V / 0,1 V, retards de la fiche TI (9/10 ns ; 13/25 ns), alimentation hors plage (> 7 V = puce détruite) signalée.
- **Oscilloscope** : mesures sur la fenêtre affichée avec la pleine résolution (Fréq, Max, Min, Cr-cr, Moy, Phase lue sur les courbes) ; affichage min/max (bande pleine si le signal est trop rapide, jamais de faux signal) ; déclenchement voie 1/2, front ↑/↓ (touche Trigger puis touches de côté) ; niveau hors du signal → image instable ; curseurs.
- **Vérifications** indépendantes de l'emplacement sur la plaque (bornes, valeurs des résistances, sens) ; deux pattes dans un même trou signalées.
- **Non simulé** : multimètre (TP1 B), bruit, quantification, tolérance des composants, compteur synchrone (bonus TP3 : câblable, non vérifié par un corrigé).
- Paramètres « à vérifier » sur le vrai banc : saturation (±12,5 V retenu), seuil TTL, résistances de sortie TTL, temps de montée du GBF (10 ns supposé).

## Signaler une erreur
Bouton **⚑ Signaler une erreur** en haut à droite de l'app : il ouvre un formulaire GitHub (Issue) déjà rempli avec le montage, ton câblage et la version. L'auteur rassemble les retours avec `python tools/feedback.py`.

## Corriger une erreur
Les montages sont des fichiers YAML dans `montages/`. Voir `docs/MODIFIER_APRES_VERIF.md` (quel fichier ouvrir selon l'erreur) puis :
```
python tools/build_app.py && node tests/engine_test.js
```
Merci de noter chaque correction dans `CORRECTIONS.md` et de proposer une Pull Request.

## Extraits du sujet
L'app affiche des captures du sujet de TP (énoncés, schémas, annexes appareils) pour s'entraîner dans les mêmes conditions. Ce contenu vient de l'établissement : il est inclus à titre d'entraînement (`app/sujet_data.js`, généré par `tools/sujet_crops.py` à partir des PDF) et sera **retiré sur simple demande de l'établissement**. Le code, lui, est sous licence MIT ci-dessous ; la licence ne couvre pas ces extraits.

## Licence
MIT (voir `LICENSE`).
