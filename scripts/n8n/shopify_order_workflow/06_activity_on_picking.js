// Node type: Code (Run Once for All Items)
// Only runs if picking_id is present (confirmed sale.order)
// Input: previous output
// Output: same + activity_id

const input = $input.first().json;
const { picking_id, shopify_order_number, customer_email, order_number } = input;

if (!picking_id) {
  // Pass-through: no activity to create (draft case)
  return [{ json: { ...input, activity_id: null } }];
}

const pickingModelId = (await odooExecute.call(this, 'ir.model', 'search',
  [[['model', '=', 'stock.picking']]], { limit: 1 }))[0];

const activityTypeIds = await odooExecute.call(this, 'mail.activity.type', 'search',
  [[['category', '=', 'default']]], { limit: 1 });
const activityTypeId = activityTypeIds.length ? activityTypeIds[0] : false;

const activityId = await odooExecute.call(this, 'mail.activity', 'create', [{
  res_model_id: pickingModelId,
  res_id: picking_id,
  activity_type_id: activityTypeId,
  summary: `Répartir en cartons et imprimer BL — Shopify #${shopify_order_number}`,
  note: `Commande Shopify #${shopify_order_number} — ${customer_email || 'email manquant'} — sale.order ${order_number}.<br>Cliquer "Répartir en cartons" puis imprimer "Bon de livraison MyLab".`,
  user_id: 8,
}]);

return [{ json: { ...input, activity_id: activityId } }];
