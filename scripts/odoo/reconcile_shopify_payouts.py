"""Match Stripe/Shopify/Alma payouts (LCL bank lines) to SHOP journal payments.

Algorithm:
  For each LCL inbound line tagged Shopify/Stripe/Alma:
    Find the subset of unmatched SHOP payments whose sum is in
    [bank_amount, bank_amount * (1 + MAX_FEE_PCT)].
    The diff = fee retained by Stripe/Alma.

Dry-run by default. Pass --apply to actually create reconciliation entries.

Usage:
  python reconcile_shopify_payouts.py --statement-id 1
  python reconcile_shopify_payouts.py --statement-id 1 --apply
"""
import argparse
import sys
import xmlrpc.client
from itertools import combinations

sys.stdout.reconfigure(encoding="utf-8")

URL = "https://odoo.startec-paris.com"
DB = "OdooYJ"
UID = 8
PWD = "e6d35b4261b948664841075e8fffc3510c8db437"
COMPANY = 3

JOURNAL_SHOP = 26               # SHOP journal (Shopify Payments en transit)
JOURNAL_BANK = 14               # BNK1 (LCL)
ACCOUNT_TRANSIT_ID = 1310       # 512002 Outstanding Receipts — where SHOP payments accumulate
ACCOUNT_FEES_ID = 1112          # 627800 Other expenses and commissions
ACCOUNT_SUSPENSE_BNK1 = 968     # 471000 Suspense accounts (BNK1 suspense_account_id)

MAX_FEE_PCT = 0.06              # accept subsets summing up to +6% of bank line
MAX_AUTO_APPLY_FEE_PCT = 0.05   # only auto-apply when fee <= 5% (skip uncertain)

REF_KEYWORDS = ("SHOPIFY", "STRIPE", "ALMA")


def odoo():
    return xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")


def call(model, method, args, kwargs=None):
    return odoo().execute_kw(DB, UID, PWD, model, method, args, kwargs or {})


def detect_accounts():
    """No-op: account IDs are hardcoded after detection."""
    pass


def subset_sum_search(amounts, target_min, target_max, max_size=12):
    """Find a subset of amounts whose sum is in [target_min, target_max].
    Returns (indices, total) or (None, None) if no fit.
    Greedy first then exhaustive small combos."""
    # Greedy: sort descending, accumulate
    idx_sorted = sorted(range(len(amounts)), key=lambda i: -amounts[i])
    selected, total = [], 0.0
    for i in idx_sorted:
        if total + amounts[i] <= target_max + 0.01:
            selected.append(i)
            total += amounts[i]
            if total >= target_min - 0.01:
                # check if we're in range
                if target_min - 0.01 <= total <= target_max + 0.01:
                    return selected, total
    if target_min - 0.01 <= total <= target_max + 0.01:
        return selected, total

    # Exhaustive small combos (for small N)
    if len(amounts) > 30:
        return None, None  # too large
    for r in range(1, min(max_size, len(amounts)) + 1):
        for combo in combinations(range(len(amounts)), r):
            s = sum(amounts[i] for i in combo)
            if target_min - 0.01 <= s <= target_max + 0.01:
                return list(combo), s
    return None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--statement-id', type=int, required=True)
    parser.add_argument('--apply', action='store_true', help='Execute reconciliation (default: dry-run)')
    parser.add_argument('--limit', type=int, default=0, help='Process only N first eligible lines (apply mode)')
    args = parser.parse_args()

    detect_accounts()

    # Load LCL inbound lines tagged Shopify/Stripe/Alma
    lcl_lines = call('account.bank.statement.line', 'search_read',
                     [[['statement_id', '=', args.statement_id], ['amount', '>', 0]]],
                     {'fields': ['id', 'date', 'amount', 'payment_ref', 'is_reconciled'],
                      'order': 'date asc, id asc'})
    targets = [l for l in lcl_lines
               if any(k in (l.get('payment_ref') or '').upper() for k in REF_KEYWORDS)
               and not l.get('is_reconciled')]
    print(f"=== {len(targets)} lignes LCL Shopify/Alma non réconciliées ===\n")

    # Load SHOP payments whose 512002 line is not yet reconciled
    payments = call('account.payment', 'search_read',
                    [[['journal_id', '=', JOURNAL_SHOP], ['state', '=', 'paid']]],
                    {'fields': ['id', 'name', 'date', 'amount', 'partner_id', 'memo', 'move_id']})
    pool = []
    for p in payments:
        # Check whether the 512002 line of this payment's move is still unreconciled
        transit_lines = call('account.move.line', 'search_read',
            [[['move_id', '=', p['move_id'][0]],
              ['account_id', '=', ACCOUNT_TRANSIT_ID],
              ['reconciled', '=', False]]],
            {'fields': ['id']})
        if transit_lines:
            p['_transit_line_id'] = transit_lines[0]['id']
            pool.append(p)
    print(f"Pool: {len(pool)} paiements SHOP non encore rapprochés (total +{sum(p['amount'] for p in pool):.2f} €)\n")

    matched_payment_ids = set()
    proposals = []

    for lcl in targets:
        # Available pool = those not yet allocated
        avail = [(i, p) for i, p in enumerate(pool) if p['id'] not in matched_payment_ids]
        amounts = [p['amount'] for _, p in avail]
        if not amounts:
            proposals.append({'lcl': lcl, 'matched': [], 'sum': 0, 'fee': None, 'status': 'no_pool'})
            continue

        target = lcl['amount']
        sel_idx, total = subset_sum_search(amounts, target, target * (1 + MAX_FEE_PCT))
        if sel_idx is None:
            proposals.append({'lcl': lcl, 'matched': [], 'sum': 0, 'fee': None, 'status': 'no_match'})
            continue

        selected_payments = [avail[i][1] for i in sel_idx]
        for p in selected_payments:
            matched_payment_ids.add(p['id'])
        fee = total - target
        proposals.append({'lcl': lcl, 'matched': selected_payments, 'sum': total,
                          'fee': fee, 'status': 'matched'})

    # Report
    print(f"{'='*100}")
    print(f"{'LCL date':12s} {'LCL +EUR':>10s} {'Brut SHOP':>11s} {'Frais':>8s} {'Frais %':>8s} {'N paie':>6s}  Détail")
    print(f"{'-'*100}")
    total_lcl = total_brut = total_fees = 0.0
    matched_count = 0
    for p in proposals:
        lcl = p['lcl']
        status = p['status']
        if status == 'matched':
            matched_count += 1
            total_lcl += lcl['amount']; total_brut += p['sum']; total_fees += p['fee']
            fee_pct = p['fee'] / lcl['amount'] * 100
            paid_to = [pm['partner_id'][1].split(',')[0][:18] if pm.get('partner_id') else '-' for pm in p['matched'][:3]]
            extra = f" ...+{len(p['matched'])-3}" if len(p['matched']) > 3 else ''
            detail = ' / '.join(paid_to) + extra
            print(f"{lcl['date']:12s} {lcl['amount']:>10.2f} {p['sum']:>11.2f} {p['fee']:>8.2f} {fee_pct:>7.2f}% {len(p['matched']):>6d}  {detail}")
        else:
            label = 'AUCUN MATCH' if status == 'no_match' else 'POOL VIDE'
            print(f"{lcl['date']:12s} {lcl['amount']:>10.2f} {'-':>11s} {'-':>8s} {'-':>8s} {'-':>6s}  ⚠ {label}")

    print(f"{'-'*100}")
    print(f"  {matched_count}/{len(targets)} LCL appariées | Brut SHOP: {total_brut:.2f} € | Frais: {total_fees:.2f} € ({total_fees/total_lcl*100 if total_lcl else 0:.2f}%)")
    print(f"  Reste pool SHOP: {len(pool) - len(matched_payment_ids)} paiements non appariés")

    if not args.apply:
        print(f"\n[DRY-RUN] Aucune écriture créée. Relance avec --apply [--limit N] pour exécuter.")
        return

    # === APPLY MODE ===
    print(f"\n[APPLY MODE] Réconciliation des matchings dont frais <= {MAX_AUTO_APPLY_FEE_PCT*100:.0f}%")
    if args.limit:
        print(f"  --limit {args.limit} → ne traite que les {args.limit} premières lignes éligibles")

    applied = 0
    attempted = 0
    skipped_high_fee = 0
    errors = []
    for prop in proposals:
        if prop['status'] != 'matched':
            continue
        lcl = prop['lcl']
        fee_pct = prop['fee'] / lcl['amount']
        if fee_pct > MAX_AUTO_APPLY_FEE_PCT:
            skipped_high_fee += 1
            print(f"  SKIP {lcl['date']} +{lcl['amount']:.2f} € (frais {fee_pct*100:.2f}% > seuil)")
            continue
        if args.limit and attempted >= args.limit:
            break
        attempted += 1
        try:
            apply_one(lcl, prop['matched'], prop['sum'], prop['fee'])
            applied += 1
            print(f"  ✓ {lcl['date']} +{lcl['amount']:.2f} € apparié à {len(prop['matched'])} paiement(s), frais {prop['fee']:.2f} €")
        except Exception as e:
            err = f"{lcl['date']} +{lcl['amount']:.2f} → {str(e)[:200]}"
            errors.append(err)
            print(f"  ✗ {err}")

    print(f"\n=== APPLY DONE ===")
    print(f"  Appliquées : {applied}")
    print(f"  Skippées (frais > seuil) : {skipped_high_fee}")
    print(f"  Erreurs : {len(errors)}")
    for e in errors:
        print(f"   - {e}")


def safe_call(model, method, args, kwargs=None):
    """Wrap call() to swallow the cosmetic 'cannot marshal None' XML-RPC fault."""
    try:
        return call(model, method, args, kwargs)
    except xmlrpc.client.Fault as e:
        if 'marshal None' in (e.faultString or ''):
            return None
        raise


def apply_one(lcl, matched_payments, brut, fee):
    """Reconcile one bank line with its matched SHOP payments + fee writeoff.

    Mechanism:
      Bank line's move is in DRAFT state (statement not validated yet).
      Lines initially: dr 512001 X_net / cr 471000 (suspense) X_net.
      We atomically replace the suspense line with:
        - cr 512002 brut  (closes SHOP outstanding receipts)
        - dr 627800 fee   (Stripe/Alma fees), if fee > 0
      Then post the move and reconcile the new 512002 cr line with the
      existing 512002 dr lines from the matched SHOP payments.
    """
    bsl_id = lcl['id']
    bsl = call('account.bank.statement.line', 'read', [[bsl_id]],
               {'fields': ['move_id', 'is_reconciled']})
    if bsl[0]['is_reconciled']:
        raise Exception("already reconciled")
    move_id = bsl[0]['move_id'][0]

    move = call('account.move', 'read', [[move_id]], {'fields': ['state']})
    state = move[0]['state']
    if state == 'posted':
        # Move was posted (statement was validated) — need to draft first
        safe_call('account.move', 'button_draft', [[move_id]])
    elif state != 'draft':
        raise Exception(f"unexpected move state {state}")

    # Find suspense line
    suspense_lines = call('account.move.line', 'search_read',
        [[['move_id', '=', move_id], ['account_id', '=', ACCOUNT_SUSPENSE_BNK1]]],
        {'fields': ['id', 'credit', 'debit']})
    if len(suspense_lines) != 1:
        raise Exception(f"expected 1 suspense line, found {len(suspense_lines)}")
    if abs(suspense_lines[0]['credit'] - lcl['amount']) > 0.01:
        raise Exception(f"suspense credit ({suspense_lines[0]['credit']}) != bank amount ({lcl['amount']})")

    # Atomic write: unlink suspense + add counterpart lines (must balance in one op)
    write_lines = [
        (2, suspense_lines[0]['id']),
        (0, 0, {
            'account_id': ACCOUNT_TRANSIT_ID,
            'credit': round(brut, 2), 'debit': 0,
            'name': f"Encaissement Shopify — {lcl.get('payment_ref','')}"[:64],
        }),
    ]
    if fee > 0.005:
        write_lines.append((0, 0, {
            'account_id': ACCOUNT_FEES_ID,
            'debit': round(fee, 2), 'credit': 0,
            'name': f"Frais Stripe/Alma — {lcl.get('payment_ref','')}"[:64],
        }))
    call('account.move', 'write', [[move_id], {'line_ids': write_lines}])

    # Post (may raise cosmetic marshal None)
    safe_call('account.move', 'action_post', [[move_id]])

    # Reconcile: new 512002 cr line + SHOP payments' 512002 dr lines
    new_transit = call('account.move.line', 'search_read',
        [[['move_id', '=', move_id], ['account_id', '=', ACCOUNT_TRANSIT_ID]]],
        {'fields': ['id', 'reconciled']})
    if not new_transit or new_transit[0]['reconciled']:
        raise Exception("new 512002 line missing or already reconciled")
    new_id = new_transit[0]['id']

    payment_transit_ids = [p['_transit_line_id'] for p in matched_payments]

    safe_call('account.move.line', 'reconcile', [[new_id] + payment_transit_ids])

    # Verify the bank line is now reconciled
    bsl_after = call('account.bank.statement.line', 'read', [[bsl_id]], {'fields': ['is_reconciled']})
    if not bsl_after[0]['is_reconciled']:
        raise Exception("bank line still not reconciled after reconcile() call")


if __name__ == '__main__':
    main()
