// === BUSINESS LOGIC: Register Payment for each just-posted invoice ===
// Reads invoice_ids from upstream "Create Invoice" output.
// For each posted, non-paid out_invoice: registers an inbound payment
// on journal SHOP (Shopify Payments en transit) via account.payment.register wizard.
// Idempotent: skips invoices already paid.

const SHOPIFY_JOURNAL_ID = 26;   // SHOP - Shopify Payments en transit
const SHOPIFY_PML_ID = 17;       // Manual Payment line for SHOP journal

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
const invoice_ids = Array.isArray(input.invoice_ids) ? input.invoice_ids : [];

if (!invoice_ids.length) {
  out.payment_status = 'skipped';
  out.payment_reason = 'no invoice_ids in payload';
  return [{ json: out }];
}

try {
  const invs = await odooExecute.call(this, 'account.move', 'read',
    [invoice_ids],
    { fields: ['id', 'name', 'state', 'payment_state', 'move_type', 'amount_residual', 'invoice_date', 'invoice_origin'] });

  const paid = [];
  const skipped = [];
  const failed = [];

  for (const inv of invs) {
    if (inv.state !== 'posted') {
      skipped.push({ id: inv.id, reason: `state=${inv.state}` });
      continue;
    }
    if (inv.payment_state === 'paid') {
      skipped.push({ id: inv.id, reason: 'already paid' });
      continue;
    }
    if (inv.move_type !== 'out_invoice') {
      skipped.push({ id: inv.id, reason: `move_type=${inv.move_type}` });
      continue;
    }

    const ctx = {
      active_model: 'account.move',
      active_ids: [inv.id],
      active_id: inv.id,
    };

    const wizRes = await safeExecute.call(this, 'account.payment.register', 'create',
      [{
        journal_id: SHOPIFY_JOURNAL_ID,
        payment_method_line_id: SHOPIFY_PML_ID,
        amount: inv.amount_residual,
        payment_date: inv.invoice_date,
        communication: `Shopify Order ${inv.invoice_origin || ''}`.trim(),
      }], { context: ctx });

    if (!wizRes.ok) {
      failed.push({ id: inv.id, name: inv.name, error: `wizard create: ${wizRes.error}` });
      continue;
    }

    const actRes = await safeExecute.call(this, 'account.payment.register', 'action_create_payments',
      [[wizRes.result]], { context: ctx });
    if (!actRes.ok) {
      failed.push({ id: inv.id, name: inv.name, error: `action_create_payments: ${actRes.error}` });
      continue;
    }

    // Verify the invoice is now paid
    const inv2 = await odooExecute.call(this, 'account.move', 'read',
      [[inv.id]], { fields: ['payment_state'] });
    if (inv2[0] && inv2[0].payment_state === 'paid') {
      paid.push({ id: inv.id, name: inv.name });
    } else {
      failed.push({ id: inv.id, name: inv.name, payment_state: inv2[0] && inv2[0].payment_state });
    }
  }

  out.payment_status = failed.length ? 'partial' : (paid.length ? 'paid' : 'skipped');
  out.payment_paid = paid;
  if (skipped.length) out.payment_skipped = skipped;
  if (failed.length) out.payment_failed = failed;
} catch (e) {
  out.payment_status = 'failed';
  out.payment_error = String(e && e.message || e);
}

return [{ json: out }];
