# Fiches produits — Gamme Fortifiante (Swertia Japonica)

Source technique : Favre Cosmetics (même façonnier). Statut : **texte validé par Yoann**, non poussé dans Shopify.

**Principe de rédaction retenu : zéro risque réglementaire.** En cas de doute, on ne mentionne rien. Sont donc absents des descriptions : les allégations d'efficacité non substantiées (croissance, chute, microcirculation, action sur le follicule), les pourcentages d'origine naturelle non confirmés, la mention « made in France » et la mention « Vegan ». Seules subsistent les mentions « sans … » explicitement annoncées par le façonnier et la description factuelle de l'usage.

---

## 1. Shampoing fortifiant

**Titre Shopify :** Shampoing fortifiant
**Handles :** `shampoing-fortifiant` (200ml) · `shampoing-fortifiant-500ml` · `shampoing-fortifiant-1000-ml`
**Type :** Gamme mixte > Les Fortifiants
**Tags :** `200ml` (resp. `500ml`, `1000ml`), `Les Fortifiants`, `fortifiant`, `shampoing`, `Shampoings`
**Prix HT (Odoo) :** 200ml 8,00 € · 500ml 16,90 € · 1000ml 27,90 €

### Description shampoing (body_html)

```html
<p>Le <strong>Shampoing fortifiant</strong> à l'<strong>extrait de Swertia Japonica</strong> est un soin lavant formulé pour les cheveux affaiblis et les cuirs chevelus qui manquent de tonus. Sa base lavante douce, sans sulfates, nettoie sans agresser la fibre ni décaper le cuir chevelu. Sa texture souple s'émulsionne facilement et se rince sans résidu, laissant les cheveux légers et faciles à coiffer. Il constitue la première étape de la routine fortifiante, avant l'application du sérum.</p><ul>
<li>
<strong>Type de cheveux :</strong> Cheveux affaiblis ou fins — cuir chevelu en manque de tonus</li>
<li>
<strong>Résultat :</strong> Cheveux propres, souples et légers — cuir chevelu respecté</li>
</ul><p><strong>Conseil d'utilisation :</strong> Répartir sur cheveux mouillés, émulsionner, laisser poser 3 minutes puis rincer. Renouveler si nécessaire. En routine : 2 à 3 lavages par semaine pendant 7 à 8 semaines, en association avec le sérum fortifiant.</p><p><em>Produit professionnel • Sans sulfate • Sans parabène • Sans silicone • Sans phénoxyéthanol • Sans colorant • Marque blanche disponible</em></p>
```

### INCI shampoing (usage interne — à faire confirmer par le façonnier avant publication)

AQUA, SODIUM LAUROYL METHYL ISETHIONATE, SODIUM METHYL OLEOYL TAURATE, COCAMIDOPROPYL BETAINE, SODIUM CHLORIDE, SWERTIA JAPONICA EXTRACT, PARFUM, GUAR HYDROXYPROPYLTRIMONIUM CHLORIDE, LEVULINIC ACID, TRISODIUM ETHYLENEDIAMINE DISUCCINATE, SODIUM LEVULINATE, SODIUM BENZOATE, GLYCERIN, BUTYLENE GLYCOL, LIMONENE, HEXYL CINNAMAL, BENZYL SALICYLATE, HYDROXYCITRONELLAL.

---

## 2. Sérum fortifiant

**Titre Shopify :** Sérum fortifiant
**Handle :** `serum-fortifiant` (50ml)
**Type :** Gamme mixte > Les Fortifiants
**Tags :** `50ml`, `Les Fortifiants`, `fortifiant`, `sérum`, `Soins`
**Prix HT (Odoo) :** 12,50 €

### Description sérum (body_html)

```html
<p>Le <strong>Sérum fortifiant</strong> à l'<strong>extrait de Swertia Japonica</strong> est un soin sans rinçage destiné au cuir chevelu, à appliquer raie par raie après le shampoing. Sa texture fluide pénètre instantanément et ne laisse aucun résidu : ni effet gras, ni cheveux alourdis, ni contrainte de coiffage. Il complète le shampoing fortifiant au sein d'une routine à mener sur 7 à 8 semaines.</p><ul>
<li>
<strong>Type de cheveux :</strong> Tous types de cheveux — application sur cuir chevelu</li>
<li>
<strong>Résultat :</strong> Cuir chevelu traité en profondeur, sans effet gras ni résidu</li>
</ul><p><strong>Conseil d'utilisation :</strong> Appliquer par raies sur cheveux essorés ou secs, après le shampoing fortifiant. Masser du bout des doigts pour faire pénétrer. Ne pas rincer. Laisser sécher à l'air libre ou procéder au brushing. 2 à 3 applications par semaine pendant 7 à 8 semaines.</p><p><em>Produit professionnel • Sans sulfate • Sans parabène • Sans silicone • Sans phénoxyéthanol • Sans colorant • Marque blanche disponible</em></p>
```

### INCI sérum (usage interne — à faire confirmer par le façonnier avant publication)

AQUA, ALCOHOL, GLYCERIN, BENZYL ALCOHOL, PENTYLENE GLYCOL, DIETHYL PHTHALATE, BUTYLENE GLYCOL, SWERTIA JAPONICA EXTRACT, DISODIUM ADENOSINE TRIPHOSPHATE, POTASSIUM SORBATE, GLYCOPROTEINS.

---

## À demander au façonnier pour enrichir les fiches plus tard

Chaque point ci-dessous est actuellement **absent des descriptions** faute de confirmation. Dès qu'un élément est confirmé par écrit, il peut être réintégré.

| Élément retiré | Ce qu'il faut obtenir pour le remettre |
| --- | --- |
| % d'ingrédients d'origine naturelle | La valeur exacte par référence (Favre annonce « 96 %/95 % » sans préciser lequel est lequel) |
| Allégations pousse / chute / follicule | Un test d'efficacité ou un dossier de substantiation (règlement UE 655/2013) |
| Rôle actif de l'ATP et des glycoprotéines | Idem — les ingrédients ne sont plus nommés dans la description tant que leur effet n'est pas documenté |
| « 100 % made in France » | Le lieu de fabrication réel du jus |
| « Vegan » | L'origine des glycoprotéines du sérum |
| Publication de l'INCI | La fiche technique MY.LAB signée — en particulier le statut du `DIETHYL PHTHALATE` du sérum (dénaturant de l'alcool, mais un phtalate reste attaquable par un client pro) |

## Autres points ouverts

- **Nom de gamme** — « Les Fortifiants » : **validé** (20/07/2026).
- **1000 ml** — pas de paliers dégressifs définis dans Odoo pour ce format ([create_fortifiant.py](../../scripts/odoo/create_fortifiant.py#L19-L21)).
- **Création Shopify** — **faite le 20/07/2026**, les 4 fiches sont en **brouillon** via [create_fortifiant_products.py](../../scripts/shopify/create_fortifiant_products.py) :

  | Handle | ID | SKU | Prix HT |
  | --- | --- | --- | --- |
  | `shampoing-fortifiant` | 15942591971662 | shampoing-fortifiant-200-ml | 8,00 € |
  | `shampoing-fortifiant-500ml` | 15942592004430 | shampoing-fortifiant-500-ml | 16,90 € |
  | `shampoing-fortifiant-1000-ml` | 15942592069966 | shampoing-fortifiant-1000-ml | 27,90 € |
  | `serum-fortifiant` | 15942592135502 | serum-fortifiant-50-ml | 12,50 € |

  Restent à faire avant passage en `active` : visuels produits, rattachement aux collections, paliers de volume (One Stop), et vérification du stock (la sync Odoo→Shopify est un miroir exact, 0 inclus).
