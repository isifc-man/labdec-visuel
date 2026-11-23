# LABDEC_VISUEL — banc d'électronique virtuel

Simulateur de TP d'électronique (plaque d'essai, générateur, oscilloscope, alimentation) : on câble comme sur la vraie plaque et **les écrans des appareils se calculent à partir du câblage**. Tout tourne dans le navigateur, hors ligne, sans serveur.

> Projet étudiant indépendant. Non affilié à Keysight ni à l'établissement. Les noms d'appareils ne servent qu'à décrire le matériel simulé.

## Utiliser
**Lien direct : https://manprofessionalenterprises.github.io/labdec-visuel/**  (rien à installer, fonctionne aussi hors ligne une fois chargé)

Ouvrir le lien de l'application (GitHub Pages) ou, en local : `python tools/build_app.py` puis ouvrir `out/labdec_app.html`. Prérequis : Python 3 + `pip install pyyaml`, Node.js pour les tests.

## Ce qui est simulé (et ce qui ne l'est pas)
- Simulé : circuits analogiques linéaires, AOP TL081 (bande passante, vitesse de montée, saturation), charge du GBF (50 Ω) et de l'oscillo (1 MΩ ∥ 16 pF), erreurs de câblage (AOP non alimenté, 0 V d'alim flottant).
- **Non simulé** : TP3 (74LS00, 74LS74), LED. L'écran le dit au lieu d'inventer un signal.
- Pas de bruit, de quantification, de tolérance des composants.

## Signaler une erreur
Bouton **⚑ Signaler une erreur** en haut à droite de l'app : il ouvre un formulaire GitHub (Issue) déjà rempli avec le montage, ton câblage et la version. L'auteur rassemble les retours avec `python tools/feedback.py`.

## Corriger une erreur
Les montages sont des fichiers YAML dans `montages/`. Voir `docs/MODIFIER_APRES_VERIF.md` (quel fichier ouvrir selon l'erreur) puis :
```
python tools/build_app.py && node tests/engine_test.js
```
Merci de noter chaque correction dans `CORRECTIONS.md` et de proposer une Pull Request.

## Extraits du sujet
Les captures du sujet de TP (énoncés, annexes) appartiennent à l'établissement et **ne sont pas dans ce dépôt**. Si les PDF `Sujet TP 1/2/3` sont présents au moment du build (`LABDEC_SUJET_DIR=/dossier`), `tools/sujet_crops.py` les découpe et les intègre à ta copie locale ; sinon l'app affiche le texte des fichiers montage.

## Licence
MIT (voir `LICENSE`).
