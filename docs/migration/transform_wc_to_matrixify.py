"""
Transform WebToffee Pro WC export CSVs (Orders + Users) into Matrixify Shopify
import-ready CSVs (Orders sheet + Customers sheet).

USAGE:
  python transform_wc_to_matrixify.py \
    --orders C:/Users/startec/Downloads/order_export_*.csv \
    --users  C:/Users/startec/Downloads/user_export_*.csv \
    --out    d:/be-yours-mylab/docs/migration/

OUTPUTS (in --out dir):
  - matrixify_orders.csv     (sheet "Orders")
  - matrixify_customers.csv  (sheet "Customers")
  - transform_log.txt        (skip reasons + counters)

FILTERS:
  - Orders: status not in (ywraq-*, trash); order_date >= --cutoff (default 2026-02-26)
  - Users:  user_registered >= --cutoff
  - Orders: Name (#order_number) not in --shopify-existing list (collision-safe)

Tags Command: MERGE on customers (so existing tags like dossier-valide/pro stay).
"""
import argparse, csv, glob, os, re, sys
from datetime import datetime

# WC status -> (Payment: Status, Fulfillment kind)
# Fulfillment kind: 'success' = create a Fulfillment Line sub-row with Status=success;
#                   'cancelled' = Fulfillment Line with Status=cancelled
#                   '' = no Fulfillment Line (order stays unfulfilled)
STATUS_MAP = {
    'completed':         ('paid',      'success'),
    'wc-completed':      ('paid',      'success'),
    'shipped':           ('paid',      'success'),
    'wc-shipped':        ('paid',      'success'),
    'delivered':         ('paid',      'success'),
    'partial-shipped':   ('paid',      'success'),  # partial fulfillment treated as 1 successful fulfillment
    'processing':        ('paid',      ''),
    'wc-processing':     ('paid',      ''),
    'en-cours-de-prepa': ('paid',      ''),
    'on-hold':           ('pending',   ''),
    'wc-on-hold':        ('pending',   ''),
    'pending':           ('pending',   ''),
    'wc-pending':        ('pending',   ''),
    'cancelled':         ('voided',    ''),
    'wc-cancelled':      ('voided',    ''),
    'failed':            ('voided',    ''),
    'wc-failed':         ('voided',    ''),
    'refunded':          ('refunded',  ''),
    'wc-refunded':       ('refunded',  ''),
}
SKIP_STATUSES = {
    'ywraq-pending', 'wc-ywraq-pending',
    'ywraq-new', 'wc-ywraq-new',
    'trash', 'wc-trash',
}

# Output column lists (Matrixify Orders schema — strict)
ORDER_COLS = [
    'Name', 'Command',
    'Email', 'Phone',
    'Customer: Email', 'Customer: Phone',
    'Customer: First Name', 'Customer: Last Name',
    'Currency', 'Tax: Included',
    'Created At', 'Processed At',
    'Note', 'Tags', 'Tags Command',
    'Source',
    'Payment: Status',
    'Send Receipt',
    'Billing: First Name', 'Billing: Last Name', 'Billing: Phone', 'Billing: Company',
    'Billing: Address 1', 'Billing: Address 2', 'Billing: City', 'Billing: Province',
    'Billing: Zip', 'Billing: Country', 'Billing: Country Code',
    'Shipping: First Name', 'Shipping: Last Name', 'Shipping: Phone', 'Shipping: Company',
    'Shipping: Address 1', 'Shipping: Address 2', 'Shipping: City', 'Shipping: Province',
    'Shipping: Zip', 'Shipping: Country', 'Shipping: Country Code',
    # Line columns (sub-rows fill these, header row has the first line item)
    'Line: Type', 'Line: Title', 'Line: SKU',
    'Line: Quantity', 'Line: Price', 'Line: Taxable',
    # Transaction sub-row columns
    'Transaction: Kind', 'Transaction: Status', 'Transaction: Amount',
    'Transaction: Gateway', 'Transaction: Authorization', 'Transaction: Force Gateway',
    # Fulfillment sub-row columns
    'Fulfillment: ID', 'Fulfillment: Status', 'Fulfillment: Location',
]

CUSTOMER_COLS = [
    'Email', 'First Name', 'Last Name', 'Phone',
    'Tags', 'Tags Command',
    'Note', 'Verified Email', 'Tax Exempt',
    'Address: First Name', 'Address: Last Name',
    'Address: Company', 'Address: Phone',
    'Address Line 1', 'Address Line 2',
    'Address: City', 'Address: Province',
    'Address: Zip', 'Address: Country', 'Address: Country Code',
]


def parse_line_item(s):
    """Parse 'name:X|product_id:Y|sku:Z|quantity:1|total:99|sub_total:99|tax:19.8|...|meta:k:v|_variation_id:N'
    into a dict. The colon-after-meta is itself k:v."""
    if not s:
        return None
    out = {'_meta': {}}
    parts = s.split('|')
    i = 0
    while i < len(parts):
        p = parts[i]
        if not p:
            i += 1; continue
        if p.startswith('meta:'):
            # 'meta:key:value'
            kv = p[5:]
            if ':' in kv:
                k, v = kv.split(':', 1)
                out['_meta'][k] = v
            i += 1; continue
        if p.startswith('tax_data:'):
            # tax_data is followed by serialized PHP, possibly containing '|' itself.
            # Skip until next 'name:' or 'meta:' or known prefix.
            i += 1
            while i < len(parts) and not parts[i].startswith(('name:','meta:','sku:','total:','sub_total:','tax:','quantity:','product_id:','_variation_id:','tax_data:')):
                i += 1
            continue
        if ':' in p:
            k, v = p.split(':', 1)
            out[k] = v
        i += 1
    return out


def parse_shipping_items(s):
    if not s: return None
    out = {}
    for p in s.split('|'):
        if ':' in p:
            k, v = p.split(':', 1)
            out[k] = v
    return out


def parse_date(s):
    if not s: return None
    s = s.strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try: return datetime.strptime(s, fmt)
        except: pass
    return None


def get(d, *keys):
    for k in keys:
        v = d.get(k)
        if v: return v
    return ''


def country_code(country_field):
    """WC country may be 2-letter code already (FR) or full name. Best-effort."""
    if not country_field: return ''
    if len(country_field) == 2: return country_field.upper()
    return ''  # Matrixify can resolve from Country field too


def transform_orders(in_csv, out_csv, log_lines, cutoff_date, shopify_existing_names):
    with open(in_csv, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))

    counts = {'total': len(rows), 'before_window': 0, 'skip_status': 0, 'skip_collision': 0,
              'skip_unmapped_status': 0, 'imported': 0, 'header_rows': 0, 'sub_rows': 0}
    out_rows = []
    skipped_statuses = {}

    for r in rows:
        order_id = r.get('order_id') or r.get('order_number')
        order_date = parse_date(r.get('order_date',''))
        status = (r.get('status') or '').strip()
        order_number = r.get('order_number') or order_id
        name = '#' + str(order_number) if order_number else ''

        if not order_date or order_date.date() < cutoff_date:
            counts['before_window'] += 1
            log_lines.append(f'SKIP_DATE  {name:>10} {r.get("order_date","")}')
            continue

        if status in SKIP_STATUSES:
            counts['skip_status'] += 1
            log_lines.append(f'SKIP_STATUS  {name:>10} {status}')
            continue

        if status not in STATUS_MAP:
            counts['skip_unmapped_status'] += 1
            skipped_statuses[status] = skipped_statuses.get(status, 0) + 1
            log_lines.append(f'SKIP_UNMAPPED_STATUS  {name:>10} {status}')
            continue

        if name in shopify_existing_names:
            counts['skip_collision'] += 1
            log_lines.append(f'SKIP_COLLISION  {name}')
            continue

        payment_status, fulfillment_kind = STATUS_MAP[status]

        # Parse line items
        line_items = []
        i = 1
        while True:
            li = r.get(f'line_item_{i}')
            if li is None: break
            if li.strip():
                parsed = parse_line_item(li)
                if parsed: line_items.append(parsed)
            else:
                # also stop on first empty followed by all empties (faster)
                pass
            i += 1
            if i > 50: break

        if not line_items:
            counts['skip_unmapped_status'] += 1
            log_lines.append(f'SKIP_NO_LINES  {name:>10}')
            continue

        # Parse shipping
        shipping_info = parse_shipping_items(r.get('shipping_items', '') or '')

        # Build header row + sub-rows
        first_line = line_items[0]

        # Header row
        header = {col: '' for col in ORDER_COLS}
        header.update({
            'Name': name,
            'Command': 'NEW',
            'Email': r.get('billing_email') or r.get('customer_email') or '',
            'Phone': r.get('billing_phone',''),
            'Customer: Email': r.get('customer_email') or r.get('billing_email') or '',
            'Customer: Phone': r.get('billing_phone',''),
            'Customer: First Name': r.get('billing_first_name',''),
            'Customer: Last Name': r.get('billing_last_name',''),
            'Currency': r.get('order_currency') or 'EUR',
            'Tax: Included': 'FALSE',
            'Created At': r.get('order_date',''),
            'Processed At': r.get('paid_date','') or r.get('order_date',''),
            'Note': (r.get('customer_note') or '').replace('\n',' ').strip(),
            'Tags': 'imported-from-wc',
            'Tags Command': 'MERGE',
            'Source': 'wc_migration',
            'Payment: Status': payment_status,
            'Send Receipt': 'FALSE',
            'Billing: First Name': r.get('billing_first_name',''),
            'Billing: Last Name': r.get('billing_last_name',''),
            'Billing: Phone': r.get('billing_phone',''),
            'Billing: Company': r.get('billing_company',''),
            'Billing: Address 1': r.get('billing_address_1',''),
            'Billing: Address 2': r.get('billing_address_2',''),
            'Billing: City': r.get('billing_city',''),
            'Billing: Province': r.get('billing_state',''),
            'Billing: Zip': r.get('billing_postcode',''),
            'Billing: Country Code': country_code(r.get('billing_country','')),
            'Shipping: First Name': r.get('shipping_first_name',''),
            'Shipping: Last Name': r.get('shipping_last_name',''),
            'Shipping: Phone': r.get('shipping_phone',''),
            'Shipping: Company': r.get('shipping_company',''),
            'Shipping: Address 1': r.get('shipping_address_1',''),
            'Shipping: Address 2': r.get('shipping_address_2',''),
            'Shipping: City': r.get('shipping_city',''),
            'Shipping: Province': r.get('shipping_state',''),
            'Shipping: Zip': r.get('shipping_postcode',''),
            'Shipping: Country Code': country_code(r.get('shipping_country','')),
            # First line item embedded in header row
            'Line: Type': 'Line Item',
            'Line: Title': first_line.get('name',''),
            'Line: SKU': first_line.get('sku',''),
            'Line: Quantity': first_line.get('quantity','1'),
            'Line: Price': first_line.get('sub_total') or first_line.get('total','0'),
            'Line: Taxable': 'TRUE',
        })

        out_rows.append(header); counts['header_rows'] += 1

        # Sub-rows for additional line items
        for li in line_items[1:]:
            sub = {col: '' for col in ORDER_COLS}
            sub.update({
                'Name': name,
                'Line: Type': 'Line Item',
                'Line: Title': li.get('name',''),
                'Line: SKU': li.get('sku',''),
                'Line: Quantity': li.get('quantity','1'),
                'Line: Price': li.get('sub_total') or li.get('total','0'),
                'Line: Taxable': 'TRUE',
            })
            out_rows.append(sub); counts['sub_rows'] += 1

        # Sub-row for shipping line if any
        ship_total = r.get('shipping_total','0') or '0'
        try:
            ship_total_num = float(ship_total or 0)
        except ValueError:
            ship_total_num = 0
        if ship_total_num > 0:
            method = (shipping_info or {}).get('method_id') or r.get('shipping_method','Shipping')
            sub = {col: '' for col in ORDER_COLS}
            sub.update({
                'Name': name,
                'Line: Type': 'Shipping Line',
                'Line: Title': r.get('shipping_method','') or method,
                'Line: Price': ship_total,
            })
            out_rows.append(sub); counts['sub_rows'] += 1

        # Sub-row for transaction (only for paid orders)
        if payment_status == 'paid':
            sub = {col: '' for col in ORDER_COLS}
            sub.update({
                'Name': name,
                'Line: Type': 'Transaction',
                'Transaction: Kind': 'sale',
                'Transaction: Status': 'success',
                'Transaction: Amount': r.get('order_total',''),
                'Transaction: Gateway': r.get('payment_method','manual'),
                'Transaction: Authorization': r.get('transaction_id',''),
                'Transaction: Force Gateway': 'FALSE',  # safer: prefix "manual" to avoid re-charge
            })
            out_rows.append(sub); counts['sub_rows'] += 1

        # Sub-row for fulfillment line (only for shipped/completed/etc.)
        if fulfillment_kind == 'success':
            sub = {col: '' for col in ORDER_COLS}
            sub.update({
                'Name': name,
                'Line: Type': 'Fulfillment Line',
                'Fulfillment: ID': '1',  # all line items in same fulfillment
                'Fulfillment: Status': 'success',
            })
            out_rows.append(sub); counts['sub_rows'] += 1

        counts['imported'] += 1

    # Write output
    with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=ORDER_COLS)
        w.writeheader()
        for row in out_rows:
            w.writerow(row)

    return counts, skipped_statuses


def transform_users(in_csv, out_csv, log_lines, cutoff_date):
    with open(in_csv, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))

    counts = {'total': len(rows), 'before_window': 0, 'no_email': 0, 'imported': 0}
    out_rows = []

    for r in rows:
        registered = parse_date(r.get('user_registered',''))
        email = (r.get('user_email') or r.get('billing_email') or '').strip().lower()
        if not email:
            counts['no_email'] += 1
            continue
        if not registered or registered.date() < cutoff_date:
            counts['before_window'] += 1
            log_lines.append(f'SKIP_USER_DATE  {email:30s} {r.get("user_registered","")}')
            continue

        first = r.get('first_name') or r.get('billing_first_name') or ''
        last = r.get('last_name') or r.get('billing_last_name') or ''
        phone = r.get('billing_phone') or r.get('shipping_phone') or ''

        out = {col: '' for col in CUSTOMER_COLS}
        out.update({
            'Email': email,
            'First Name': first,
            'Last Name': last,
            'Phone': phone,
            'Tags': 'imported-from-wc,customer',
            'Tags Command': 'MERGE',
            'Verified Email': 'true',
            'Tax Exempt': 'false',
            'Address: First Name': r.get('billing_first_name',''),
            'Address: Last Name': r.get('billing_last_name',''),
            'Address: Company': r.get('billing_company',''),
            'Address: Phone': r.get('billing_phone',''),
            'Address Line 1': r.get('billing_address_1',''),
            'Address Line 2': r.get('billing_address_2',''),
            'Address: City': r.get('billing_city',''),
            'Address: Province': r.get('billing_state',''),
            'Address: Zip': r.get('billing_postcode',''),
            'Address: Country Code': country_code(r.get('billing_country','')),
        })
        out_rows.append(out); counts['imported'] += 1

    with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CUSTOMER_COLS)
        w.writeheader()
        for row in out_rows:
            w.writerow(row)

    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orders', required=True, help='WebToffee orders CSV (glob OK)')
    ap.add_argument('--users',  required=True, help='WebToffee users CSV (glob OK)')
    ap.add_argument('--out',    required=True, help='Output directory')
    ap.add_argument('--cutoff', default='2026-02-26', help='Min date (inclusive) YYYY-MM-DD')
    ap.add_argument('--shopify-existing-orders', default='', help='Comma-separated list of Shopify Names already on Shopify (e.g. #3356,#3357)')
    args = ap.parse_args()

    orders_path = sorted(glob.glob(args.orders))[-1] if '*' in args.orders else args.orders
    users_path = sorted(glob.glob(args.users))[-1] if '*' in args.users else args.users
    cutoff_date = datetime.strptime(args.cutoff, '%Y-%m-%d').date()
    shopify_existing = set(n.strip() for n in args.shopify_existing_orders.split(',') if n.strip())

    os.makedirs(args.out, exist_ok=True)
    log_lines = [f'Transform run at {datetime.now().isoformat()}',
                 f'Orders input: {orders_path}',
                 f'Users input:  {users_path}',
                 f'Cutoff date:  {cutoff_date}',
                 f'Shopify existing: {sorted(shopify_existing)}',
                 '']

    print(f'[orders] reading {orders_path}')
    o_counts, skipped_statuses = transform_orders(
        orders_path,
        os.path.join(args.out, 'matrixify_orders.csv'),
        log_lines, cutoff_date, shopify_existing
    )
    print(f'[orders] counts: {o_counts}')
    if skipped_statuses:
        print(f'[orders] unmapped statuses: {skipped_statuses}')

    print(f'[users] reading {users_path}')
    u_counts = transform_users(
        users_path,
        os.path.join(args.out, 'matrixify_customers.csv'),
        log_lines, cutoff_date
    )
    print(f'[users] counts: {u_counts}')

    log_lines.append(f'\nORDERS COUNTS: {o_counts}')
    log_lines.append(f'ORDERS UNMAPPED STATUSES: {skipped_statuses}')
    log_lines.append(f'USERS COUNTS: {u_counts}')
    with open(os.path.join(args.out, 'transform_log.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))

    print(f'\nDone. Outputs:')
    print(f'  {os.path.join(args.out, "matrixify_orders.csv")}')
    print(f'  {os.path.join(args.out, "matrixify_customers.csv")}')
    print(f'  {os.path.join(args.out, "transform_log.txt")}')


if __name__ == '__main__':
    main()
