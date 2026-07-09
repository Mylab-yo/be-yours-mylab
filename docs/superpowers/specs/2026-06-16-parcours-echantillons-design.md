# Parcours « je veux juste des échantillons » — Design

Date : 2026-06-16
Statut : validé (brainstorming), prêt pour plan d'implémentation

## Problème

Un client qui veut seulement **tester / commander des échantillons** atterrit dans la
**boutique pro** (`/pages/la-boutique-my-lab`, collection `boutique-adherents`) au lieu de la
**boutique testeurs** (`/pages/boutique-testeurs`, collection `boutique-decouverte`).

Dès qu'il ajoute un produit pro au panier, [`assets/ml-dossier-gate.js`](../../../assets/ml-dossier-gate.js)
**auto-ajoute le dossier cosmétologique** (verrouillé tant qu'un produit pro reste au panier). Le
client se retrouve **bloqué** dans le parcours de création de marque (dossier + étiquettes + produits)
sans pouvoir valider, et **sans moyen évident** d'annuler le dossier pour basculer vers les échantillons.

## Objectif

Offrir une **sortie de secours** au moment exact du blocage : un bouton dans le panier qui
**nettoie les articles de création de marque** et **redirige vers la boutique testeurs**, en un geste guidé.

Hors périmètre : prévenir l'arrivée dans la mauvaise boutique (bandeau, écran d'aiguillage). On traite
ici la **récupération**, pas la prévention.

## Décisions (validées)

| Sujet | Décision |
|-------|----------|
| Point d'entrée | Dans le **panier à l'état bloqué** (drawer ET page `/cart`) |
| Action panier | **Retirer dossier + produits pro + forfait impression + étiquettes**, puis rediriger |
| Cible redirection | `/pages/boutique-testeurs` |
| Anti-accident | Confirmation **inline en 2 temps** avant exécution |

## Déclencheur

Condition `ml_checkout_blocked` déjà calculée dans
[`sections/mini-cart.liquid`](../../../sections/mini-cart.liquid) et
[`sections/main-cart-footer.liquid`](../../../sections/main-cart-footer.liquid) :
client **non** `dossier-valide`/`pro` + produit pro au panier + parcours incomplet.

La sortie de secours ne s'affiche **que** dans cet état (le moment de friction).

## Emplacement UI

- **Drawer** : dans le `.mini-cart__footer`, **juste sous** le bouton « Passer la commande » désactivé.
  Choix volontaire : le footer est **toujours visible**, contrairement à la bulle parcours
  (`.ml-parcours-bubble`) qui est sortie en `position:fixed` sur desktop et a des aléas de portal.
- **Page `/cart`** : même bloc, même logique, dans `main-cart-footer.liquid` sous le CTA bloqué.

Style : DA MY.LAB, **DM Sans**, classes préfixées `ml-`. Lien secondaire discret, pas un 2e bouton plein.

Libellé proposé :
> *Vous vouliez seulement tester nos produits ?* **Commander des échantillons →**

## Interaction (2 temps)

1. **1er clic** sur le lien → il se remplace in-place par une confirmation :
   *« Cela retirera vos produits pro du panier. »* + bouton **[Voir les testeurs]** (+ un « Annuler » qui revient à l'état initial).
2. **Clic [Voir les testeurs]** → exécution (voir ci-dessous).

Aucune `confirm()` native (incohérent avec la DA). Confirmation purement inline/CSS+JS.

## Articles retirés — « tout le marque-création »

Au render Liquid, on identifie les lignes de panier correspondant à l'un de ces critères :

- `item.product.handle == 'creation-du-dossier-cosmetologique'` (dossier)
- produit dans la collection `boutique-adherents` (produits pro)
- `item.product.handle contains 'impression'` (forfait d'impression — cf. logique existante `ml_has_forfait`)
- produit dans la collection `modeles-detiquettes` (étiquettes)
- `item.product.handle == 'frais-de-creation-design-etiquette'` (frais création étiquette)

Les **autres** articles (ex. un testeur déjà présent) sont **conservés**.

Liquid émet la **liste des `item.key`** concernées dans un attribut `data-ml-remove-keys` sur le bouton
(séparées par virgule). Le JS lit cet attribut — **pas de re-fetch** `/cart.js` nécessaire.

## Logique JS

Handler ajouté à [`assets/mylab-cart.js`](../../../assets/mylab-cart.js), en **délégation d'événement**
sur `document` (les éléments du panier sont re-rendus en AJAX via section rendering).

À l'exécution :

1. Lire `data-ml-remove-keys` (liste de `key`).
2. `POST /cart/update.js` avec `{ updates: { "<key1>": 0, "<key2>": 0, … } }` (retrait atomique).
3. À la résolution → `window.location.href = '/pages/boutique-testeurs'`.

Pendant le retrait, afficher un état de chargement sur le bouton (spinner / disabled) pour éviter le double-clic.

### Pas de boucle avec le gate

`ml-dossier-gate.js` intercepte `/cart/update` et planifie `checkCart()` à +400 ms. Comme on retire
**tous** les produits pro en même temps, `checkCart` ne trouve plus de produit pro → **ne ré-ajoute pas**
le dossier. De plus, on **redirige avant** l'échéance des 400 ms (la page se décharge). Aucune intervention
sur le gate n'est nécessaire.

## Cas limites

- **Panier avec uniquement le dossier** (acheté seul, sans produit pro) : `ml_checkout_blocked` est faux →
  la sortie ne s'affiche pas. Comportement correct (le dossier seul est un achat légitime).
- **Plusieurs produits pro / formats** : toutes les `key` pro sont listées et retirées d'un coup.
- **Échec réseau du `/cart/update`** : ne pas rediriger ; réafficher le lien + message d'erreur discret.
- **Client `dossier-valide`/`pro`** : `ml_show_steps` faux → jamais bloqué → sortie jamais rendue.

## Fichiers touchés

| Fichier | Changement |
|---------|-----------|
| `sections/mini-cart.liquid` | Rendu du bloc sortie (footer) + calcul des `key` marque-création, sous `ml_checkout_blocked` |
| `sections/main-cart-footer.liquid` | Même bloc sortie sur la page `/cart` |
| `assets/mylab-cart.js` | Handler clic (confirm inline → `/cart/update` → redirect) |
| `assets/mylab-product.css` (ou bloc `<style>` section) | Styles `.ml-sample-exit*` (DM Sans, discret) |

## Déploiement

Assets + sections via REST PUT direct sur le thème live `#184014340430` (cf. session drawer), ou
`shopify theme push --development` puis promotion. Les sections `.liquid` modifiées invalident le cache
de rendu ; re-save / toggle si nécessaire (cf. note cache section connue).

## Vérification

1. Compte client **non** `dossier-valide`, ajouter un produit `boutique-adherents` → dossier auto-ajouté → drawer bloqué.
2. La sortie « Commander des échantillons » apparaît sous le CTA désactivé.
3. Clic → confirmation inline → clic confirm → panier vidé des articles marque-création (autres conservés) → redirection `/pages/boutique-testeurs`.
4. Le dossier **ne revient pas** (pas de boucle gate).
5. Idem sur la page `/cart`.

## Évolutions possibles (hors périmètre)

- Bandeau préventif sur la boutique pro (« vous cherchez des échantillons ? »).
- Conversion auto produit pro → testeur équivalent (nécessite un mapping de correspondance).
