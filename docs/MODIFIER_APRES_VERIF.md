# Corriger l'app après une vérification (prof ou autre)

**Principe : l'app ne contient aucune valeur « écrite dans l'écran ».** Les écrans sont calculés à partir de fichiers texte (YAML). Si quelqu'un trouve une erreur, on corrige **un fichier**, on reconstruit, et tout suit (écran, corrigé, questions, pastille de validation).

```
montages/*.yaml ─┐
hardware/*.yaml ─┼─►  tools/export_app_data.py ─► app/data.js ─┐
predictions/*.yaml┘                                             ├─► tools/build_app.py ─► out/labdec_app.html
                          app/js/*.js  app/css  app/index.html ─┘        (1 fichier autonome, hors ligne)
```

## 1. « Il y a une erreur » → quel fichier ouvrir

| L'erreur constatée | Fichier à modifier | Effet automatique |
|---|---|---|
| Un fil / une résistance / une puce n'est pas au bon trou dans le corrigé | `montages/tpN/<montage>.yaml` (`fils`, `composants`, `puces`) | le corrigé, l'écran **attendu**, la comparaison et la pastille ● changent |
| Mauvaise valeur de résistance | idem (`composants.R1.ohm`) | gain, Vpp, saturation recalculés |
| Un câble d'appareil est faux (BNC, alim, strap, T) | idem (`cables`) | prises allumées + circuit de mesure recalculés |
| Mauvais réglage de départ (GBF, alim, oscillo) | idem (`instruments.gbf.reglages`, `.psu.reglages`, `.scope.reglages`) | lu par `lesson.js › parsePreset` : garder le format `Sinus · 0,4 Vpp · 1 kHz · High Z`, `Voie 2 = +15,0 V`, `200 µs/div` |
| Mauvais nœuds à relier (checklist) | idem (`noeuds`) | checklist et validation |
| Texte du sujet, pannes, étapes | idem (`objectif`, `pannes`, `etapes_montage`) | onglet Sujet et bandeau du haut |
| Mauvaise question « à prédire » | `predictions/tpN.yaml` (`a_predire`) | onglet Questions. La réponse est calculée par le moteur, pas lue dans `attendu` |
| Plaque : géométrie, rails, sens a–e / f–j | `hardware/board_wish106.yaml` | tous les montages |
| Brochage d'une puce | `hardware/components.yaml` | |
| Position / nom d'une touche d'appareil | `app/js/faces.js` (`SPECS`, en unités de 1000 de large) | face de l'appareil |
| Menu d'un appareil (chemin High Z, softkeys) | `app/js/gbf.js`, `psu.js`, `scope.js` | |
| Paramètres physiques du TL081 (GBW 4 MHz, 13 V/µs, marge de saturation 2,5 V), GBF 50 Ω, oscillo 1 MΩ∥16 pF | **`app/js/engine.js` → `DEFAULTS`** | tous les écrans |

⚠ **Point faible connu** : `hardware/behavior.yaml` documente ces paramètres mais **le moteur ne le lit pas encore** : les valeurs sont recopiées dans `engine.js › DEFAULTS`. Si on corrige l'un, il faut corriger l'autre (à unifier : étape suivante).

## 2. Reconstruire et vérifier (3 commandes)
```
cd LABDEC_VISUEL
/usr/bin/python3 tools/build_app.py      # régénère app/data.js puis out/labdec_app.html
node tests/engine_test.js                # 21 contrôles du moteur ; doit finir par « TOUS LES TESTS PASSENT »
open out/labdec_app.html
```
Si on change une valeur de résistance d'un montage de référence, les gains attendus codés dans `tests/engine_test.js` sont à mettre à jour (c'est voulu : le test garde la mémoire des valeurs validées).

## 3. Tracer les corrections
À chaque correction demandée par quelqu'un, ajouter **une ligne** dans `CORRECTIONS.md` (date, qui, fichier, avant → après, pourquoi). Avec Git, un commit par correction : `git log -p montages/tp2/B1_inverseur.yaml` retrace l'historique d'un montage.

## 4. Ce que le moteur ne sait pas (à dire à la personne qui vérifie)
- TP3 (74LS00, 74LS74) et LED : **pas simulés**. L'écran l'affiche, il n'invente rien.
- Pas de bruit, de quantification 8 bits, de tolérance de résistance (±5 %).
- Saturation à ±12,5 V : valeur « à vérifier » (fiche TI : ±12 V min, ±13,5 V typ). Écarts déjà notés dans `TASKS.md` : fc du non-inverseur, slew rate, seuils NAND.
- Les positions de touches des faces sont relevées sur photos : approximatives.

## 5. Publier pour que d'autres l'utilisent **et** le modifient

### Ce que ChatGPT t'a répondu — suffit-il ?
La distinction « GitHub = stockage du code / hébergement = exécution » est juste. Mais **pour cette app, sa recommandation (Streamlit, React + FastAPI, Vercel) est inutilement lourde** :
- ton moteur est **déjà en JavaScript dans le navigateur** : il n'y a **aucun serveur à faire tourner** ;
- Streamlit imposerait de **réécrire** le moteur en Python et d'héberger un serveur (qui s'endort en version gratuite) ;
- React + FastAPI = deux projets à maintenir pour rien.

### La meilleure option ici : **GitHub Pages**
| | GitHub Pages | Streamlit Cloud | Vercel + backend |
|---|---|---|---|
| Coût | gratuit | gratuit (mise en veille) | gratuit puis payant |
| Serveur | aucun | oui | oui |
| Réécriture | **aucune** | tout le moteur en Python | partielle |
| Fonctionne hors ligne | oui (fichier unique ou PWA) | non | non |
| Les autres modifient | fork + Pull Request | fork | fork |
| Mise à jour | automatique à chaque `git push` | idem | idem |

Lien final du type `https://<ton-compte>.github.io/labdec-visuel/`. Une PWA (installable, hors ligne) pourra s'ajouter plus tard (un `manifest.json` + un service worker) sans changer l'app.

### Ce que j'ai préparé (rien n'est publié)
- `.gitignore` : exclut `out/`, `A_ENVOYER_PROF/`, `assets/photos/`, `.DS_Store`.
- `.github/workflows/pages.yml` : à chaque push, reconstruit l'app, lance les tests du moteur et déploie `index.html`. **Testé en local sans photos ni page de validation : le build et les 21 tests passent.**
- `README_PUBLIC.md` : présentation + « comment corriger » pour les contributeurs.

### À décider AVANT de publier (je ne le fais pas sans ton accord)
1. **Public ou privé ?** Un dépôt privé ne peut pas servir GitHub Pages en gratuit : pour un lien ouvert à tous, il faut public.
2. **Contenu de l'école.** `A_ENVOYER_PROF/` et `out/validation_*` contiennent des **extraits du sujet** de l'ISIFC : à ne pas publier sans accord de l'école. Les YAML des montages reprennent des consignes (objectifs, pannes, étapes) : à faire relire par l'enseignante avant un dépôt public.
3. **Photos du banc** (`assets/photos/`) : l'app v2 n'en a plus besoin ; les laisser hors du dépôt public.
4. **Marque** : les faces affichent « KEYSIGHT » et les modèles d'appareils. Pour un usage public, ajouter la mention « simulateur indépendant, non affilié à Keysight » (déjà dans le README préparé) ou retirer le logo.
5. **Licence** : à choisir par toi (MIT = libre réutilisation ; CC-BY-NC = pas d'usage commercial). Je n'en ai mis aucune.
6. **Dépôt dédié** : le projet se publie depuis son propre dépôt (`labdec-visuel`), jamais depuis un dépôt personnel plus large.
