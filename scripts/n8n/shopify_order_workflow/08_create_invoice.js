// Node type: Code (Run Once for All Items)
// Input: { sale_order_id, order_number, status, ... } (from 05_create_sale_order.js)
// Output: passes through input + { invoice_ids, invoice_names, invoice_status }
// Dependencies: 02_odoo_client.js prepended
//
// Flow:
//   1. If sale_order_id missing or status === 'already_processed' → passthrough
//   2. Idempotency: re-read SO, only proceed if invoice_status == 'to invoice'
//   3. Create invoice via sale.advance.payment.inv wizard (tolerant of XML-RPC marshal None)
//   4. Post each invoice (account.move.action_post)
//   5. Send email per invoice with mail.template id=18 (Invoice: Sending)
//
// Failure of any step does NOT throw — the SO is already safe. We attach
// invoice_status='failed' + error_reason for the log node downstream.

const INVOICE_TEMPLATE_ID = 18;

const input = $input.first().json;
const sale_order_id = input.sale_order_id;

// Passthrough if no SO or already processed earlier
if (!sale_order_id || input.status === 'already_processed') {
  return [{ json: { ...input, invoice_status: 'skipped' } }];
}

async function safeExecute(model, method, args, kwargs = {}) {
  try {
    return { ok: true, result: await odooExecute.call(this, model, method, args, kwargs) };
  } catch (e) {
    const msg = String(e && e.message || e);
    // Odoo XML-RPC marshals `None` on some wizard returns — cosmetic, ignore
    if (msg.includes('cannot marshal None') || msg.includes('marshal None')) {
      return { ok: true, result: null, cosmetic: true };
    }
    return { ok: false, error: msg };
  }
}

const out = { ...input };

try {
  // Step 1: Re-read SO to check idempotency
  const soList = await odooExecute.call(this, 'sale.order', 'read',
    [[sale_order_id]],
    { fields: ['invoice_status', 'state', 'client_order_ref', 'invoice_ids'] });

  if (!soList || !soList.length) {
    out.invoice_status = 'skipped';
    out.invoice_error = 'SO not found on re-read';
    return [{ json: out }];
  }
  const so = soList[0];
  if (so.state !== 'sale') {
    out.invoice_status = 'skipped';
    out.invoice_error = `SO state=${so.state} (expected 'sale')`;
    return [{ json: out }];
  }
  if (so.invoice_status !== 'to invoice') {
    out.invoice_status = 'skipped';
    out.invoice_error = `SO invoice_status=${so.invoice_status} (expected 'to invoice')`;
    return [{ json: out }];
  }
  if (!so.client_order_ref) {
    out.invoice_status = 'skipped';
    out.invoice_error = 'SO has no client_order_ref (not a Shopify order)';
    return [{ json: out }];
  }

  // Step 2: Create invoice via wizard
  const wizCtx = {
    active_model: 'sale.order',
    active_ids: [sale_order_id],
    active_id: sale_order_id,
  };
  const wizard_id = await odooExecute.call(this, 'sale.advance.payment.inv', 'create',
    [{ advance_payment_method: 'delivered' }], { context: wizCtx });

  const createRes = await safeExecute.call(this, 'sale.advance.payment.inv', 'create_invoices',
    [[wizard_id]], { context: wizCtx });
  if (!createRes.ok) {
    out.invoice_status = 'failed';
    out.invoice_error = `create_invoices failed: ${createRes.error}`;
    return [{ json: out }];
  }

  // Step 3: Re-read SO to get invoice_ids
  const so2List = await odooExecute.call(this, 'sale.order', 'read',
    [[sale_order_id]], { fields: ['invoice_ids'] });
  const inv_ids = (so2List[0] && so2List[0].invoice_ids) || [];
  if (!inv_ids.length) {
    out.invoice_status = 'failed';
    out.invoice_error = 'wizard ran but no invoice_ids on SO';
    return [{ json: out }];
  }

  // Only operate on DRAFT invoices (the new ones we just created)
  const invsRead = await odooExecute.call(this, 'account.move', 'read',
    [inv_ids], { fields: ['id', 'name', 'state'] });
  const draft_ids = invsRead.filter((i) => i.state === 'draft').map((i) => i.id);

  if (!draft_ids.length) {
    out.invoice_status = 'no_new_draft';
    out.invoice_ids = inv_ids;
    return [{ json: out }];
  }

  // Step 4: Post the draft invoices
  await odooExecute.call(this, 'account.move', 'action_post', [draft_ids]);

  // Step 5: Send email per posted invoice
  const sent_for = [];
  const send_errors = [];
  for (const iid of draft_ids) {
    const r = await safeExecute.call(this, 'mail.template', 'send_mail',
      [INVOICE_TEMPLATE_ID, iid], { force_send: true });
    if (r.ok) sent_for.push(iid);
    else send_errors.push({ inv: iid, err: r.error });
  }

  // Re-read for final names
  const final_invs = await odooExecute.call(this, 'account.move', 'read',
    [draft_ids], { fields: ['id', 'name', 'state'] });

  out.invoice_ids = draft_ids;
  out.invoice_names = final_invs.map((i) => i.name);
  out.invoice_status = send_errors.length ? 'partial' : 'invoiced_and_sent';
  if (send_errors.length) out.invoice_send_errors = send_errors;

  return [{ json: out }];
} catch (e) {
  // Last-resort catch: never block the workflow on invoice failure
  out.invoice_status = 'failed';
  out.invoice_error = String(e && e.message || e);
  return [{ json: out }];
}
