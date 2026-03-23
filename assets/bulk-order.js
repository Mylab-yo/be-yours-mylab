/**
 * ============================================================================
 * MY.LAB — Configurateur Commande Gros Volumes
 * assets/bulk-order.js
 * ============================================================================
 *
 * Logique JavaScript du configurateur multi-étapes.
 *
 * Responsabilités :
 * - Charger les données formules (bulk-data-formulas.json) et flacons (bulk-data-bottles.json)
 * - Gérer la navigation entre les 5 étapes (stepper)
 * - Peupler dynamiquement chaque étape depuis les données JSON
 * - Calculer les prix dégressifs selon les quantités
 * - Valider les saisies (quantité minimum 50kg par référence)
 * - Générer le récapitulatif
 * - Envoyer le devis via webhook (n8n ou Shopify contact)
 *
 * Config attendue dans window.BulkOrderConfig :
 *   formulasUrl : string (URL CDN du JSON formules)
 *   bottlesUrl  : string (URL CDN du JSON flacons)
 *
 * TODO:
 * - [ ] Fonction init() : charger les JSON, peupler l'étape 1
 * - [ ] Fonction renderStepper() : afficher la barre de progression
 * - [ ] Fonction goToStep(n) : navigation entre étapes
 * - [ ] Fonction renderFormulas() : étape 1 — grille des gammes
 * - [ ] Fonction renderFormats() : étape 2 — sélecteurs de format
 * - [ ] Fonction renderBottles() : étape 3 — grille des flacons
 * - [ ] Fonction renderQuantity() : étape 4 — tableau quantités + calcul
 * - [ ] Fonction renderSummary() : étape 5 — récapitulatif
 * - [ ] Fonction calculatePrice(formula, format, qty) : prix dégressif
 * - [ ] Fonction submitQuote() : envoi du devis
 * - [ ] Validation par étape avant passage à la suivante
 * - [ ] Gestion état global (formules sélectionnées, formats, flacons, qté)
 * ============================================================================
 */

(function () {
  'use strict';

  // TODO: Implémenter le configurateur

})();
