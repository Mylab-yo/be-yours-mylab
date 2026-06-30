# Écart de solde bancaire LCL (compte 512001) — note pour le comptable

**Date de l'analyse :** 30/06/2026
**Société :** SARL STARTEC (Odoo `OdooYJ`, company_id 3)
**Compte concerné :** `512001` (journal Bank `BNK1`, LCL — IBAN FR58 3000 2028 8000 0007 1073 R40)

---

## 1. Constat

Le compte bancaire **512001** dans Odoo affiche un solde **positif** alors que le compte LCL réel est **à découvert** :

| | Montant |
|---|--:|
| Solde Odoo 512001 (toutes écritures postées) | **+18 401,74 €** |
| Solde réel LCL au 29/06/2026 | **−24 899,70 €** |
| **Écart** | **≈ 43 301 €** |

## 2. Cause principale : aucun solde d'ouverture

- La **1ʳᵉ écriture** sur 512001 date du **26/02/2026** (paiement « LOVABLE DOVER » −26,68 €).
- **Aucune écriture d'à-nouveau / solde d'ouverture** n'a été posée au démarrage du suivi Odoo.
- Le compte LCL est un compte **Banque Privée à découvert permanent** (oscille entre −20 000 € et −30 000 €).
- Odoo est donc parti de **0** alors que le compte était déjà fortement négatif → tout le solde est surévalué.

### Soldes réels LCL vérifiés (lignes de solde des exports CSV LCL)

| Date | Solde réel LCL |
|---|--:|
| 01/04/2026 | −32 479,40 € |
| 05/05/2026 | −24 549,19 € |
| 29/06/2026 | −24 899,70 € |

> Note : l'export LCL en ligne est **limité à ~90 jours** (remonte au plus tôt au 01/04/2026). Le détail des transactions **26/02 → 31/03/2026** n'est pas récupérable via export CSV — à reconstituer depuis les relevés PDF papier de février/mars si besoin.

## 3. L'écart n'est PAS constant → transactions manquantes en plus

Si le seul problème était le solde d'ouverture, l'écart (GL Odoo − réel) serait **constant**. Or il varie :

| Date | Solde GL Odoo 512001 | Solde réel LCL | Écart (GL − réel) |
|---|--:|--:|--:|
| 31/03/2026 | +10 769,65 € | −32 479,40 € | 43 249,05 € |
| 05/05/2026 | +16 956,38 € | −24 549,19 € | 41 505,57 € |
| 29/06/2026 | +18 401,74 € | −24 899,70 € | 43 301,44 € |

- **Avril** : mouvement net Odoo `01/04→05/05` = **+6 186,73 €** vs réel LCL **+7 930,21 €** → **≈ 1 743 € de transactions manquantes** dans Odoo sur cette période.
- L'écart bouge encore de **~1 796 €** entre le 05/05 et le 29/06.
- Conclusion : il y a un **mélange** = solde d'ouverture manquant (~43 k) **+** transactions non saisies / éventuels doublons paiements↔relevé.

## 4. État du suivi bancaire dans Odoo par période

| Période | État |
|---|---|
| 26/02 → 05/05/2026 | Seulement des **paiements manuels épars** (aucun relevé importé). Incomplet. |
| 06/05 → 04/06/2026 | **Relevé 1** importé (145 lignes) MAIS : solde d'ouverture saisi **à tort = +14 660,05 €** (devrait être ≈ **−24 549,19 €**, soit une erreur de **39 209,24 €**) ; **jamais lettré** → 145 lignes en compte d'attente. |
| 05/06 → 29/06/2026 | **Relevé 2** importé + **lettré à 100 %** le 30/06/2026 (93 lignes). |

## 5. Comptes « argent dehors » (à rapprocher)

| Compte | Solde | Nature |
|---|--:|---|
| `511200` Encaissements en attente | **−34 019,71 €** | ALMA / Shopify reçus, non soldés contre les factures |
| `471000` Compte d'attente | **+31 216,73 €** | Lignes du relevé de mai (relevé 1) non lettrées |
| Factures clients impayées (résiduel) | **+30 010,93 €** | Dont factures d'acompte en attente d'encaissement |

## 6. Actions recommandées (à valider/réaliser avec le comptable)

1. **Poser l'écriture d'à-nouveau / solde d'ouverture** du LCL. Compte de contrepartie à décider par le comptable (report à nouveau 11x, ou compte d'attente 471 à solder). Ancre fiable : solde réel **−24 549,19 € au 05/05/2026** (jour précédant le relevé 1).
2. **Corriger le solde d'ouverture du relevé 1** (06/05) : **−24 549,19 €** au lieu de +14 660,05 €.
3. **Reconstituer / saisir les transactions manquantes** :
   - Période 01/04 → 05/05 : ≈ 1 743 € d'écart identifié (export CSV disponible).
   - Période 26/02 → 31/03 : non exportable, à reprendre depuis les relevés PDF.
4. **Lettrer le relevé 1** (145 lignes) → vider le compte d'attente 471000.
5. **Rapprocher 511200** (encaissements ALMA/Shopify) contre les factures clients → solder les ~34 k.

## 7. Pour information — opérations réalisées le 30/06/2026

- **Avoir partiel commande S00548** (client Nastia, masque boucles 400ml non livré) : **RFAC/2026/00007**, 648,00 HT + 129,60 TVA = **777,60 € TTC**, remboursé par virement, marqué **payé**.
- **Relevé LCL 05/06 → 29/06** : importé + **lettré à 100 %** (93 lignes).
