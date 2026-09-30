"""Rebuild the portfolio from local CSVs. Requires Python 3.10+, pandas, numpy.

Raw files are never modified. Outputs are deterministic for a given input snapshot.
"""
from pathlib import Path
import hashlib
import json
import sqlite3
import math
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs'
OUT.mkdir(exist_ok=True)
(OUT / 'tables').mkdir(exist_ok=True)
(OUT / 'quality').mkdir(exist_ok=True)
(OUT/'validation.json').write_text(json.dumps({'status':'running','message':'Do not publish until all checks pass'})+'\n')
data = {p.stem: pd.read_csv(p) for p in sorted((ROOT / 'data').glob('*.csv'))}
KEYS = {t: t[:-1] + '_id' for t in data}
KEYS.update(categories='category_id', order_items='order_item_id')
FKS = [('orders','customer_id','customers'),('orders','store_id','stores'),
       ('orders','promotion_id','promotions'),('order_items','order_id','orders'),
       ('order_items','product_id','products'),('products','category_id','categories'),
       ('products','supplier_id','suppliers'),('employees','store_id','stores'),
       ('payments','order_id','orders'),('shipments','order_id','orders'),
       ('returns','order_item_id','order_items')]
checks, profiles, transformations = [], [], []
def check(table, rule, count, denominator, decision):
    checks.append(dict(table=table, rule=rule, affected=int(count), population=int(denominator),
                       rate=float(count/denominator) if denominator else None, decision=decision))
def save(df, name, quality=False):
    df.to_csv(OUT / ('quality' if quality else 'tables') / (name + '.csv'), index=False)
def scalar(x):
    if isinstance(x, np.generic): return x.item()
    if isinstance(x, pd.Timestamp): return x.isoformat()
    raise TypeError(type(x).__name__)

manifest = []
for t, df in data.items():
    p = ROOT / 'data' / (t + '.csv')
    manifest.append(dict(file='data/'+p.name, rows=len(df), bytes=p.stat().st_size,
                         sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    check(t, 'duplicate_primary_key', df[KEYS[t]].duplicated().sum(), len(df), 'Stop if present: ambiguous joins')
    check(t, 'duplicate_full_row', df.duplicated().sum(), len(df), 'Stop if present: review before removing')
    for col in df:
        s = df[col]
        blank = s.isna() | s.astype('string').str.strip().eq('').fillna(False)
        check(t, 'missing_'+col, blank.sum(), len(df), 'Stop if present: required source field')
        profiles.append(dict(table=t, column=col, dtype=str(s.dtype), rows=len(df),
                             missing=int(blank.sum()), distinct=int(s.nunique()),
                             minimum=str(s.min()), maximum=str(s.max())))
        if pd.api.types.is_string_dtype(s):
            trimmed = s.str.strip()
            changed = int((s != trimmed).sum())
            df[col] = trimmed
            transformations.append(dict(table=t, transformation='trim '+col, changed=changed))
    if any(c['affected'] for c in checks if c['table']==t and (c['rule'].startswith('missing_') or c['rule'].startswith('duplicate_'))):
        save(pd.DataFrame(checks), 'checks', True)
        raise ValueError(f'{t}: structural failure; inspect quality/checks.csv')
for child, col, parent in FKS:
    bad = ~data[child][col].isin(data[parent][KEYS[parent]])
    check(child, 'unmatched_'+col, bad.sum(), len(bad), 'Stop if present: unmapped relationship')
    assert not bad.any(), (child, col)
for table, cols in {'order_items':['qty','price'], 'products':['price'], 'payments':['amount'],
                    'returns':['refund'], 'employees':['salary'], 'promotions':['discount']}.items():
    for col in cols:
        s = data[table][col]
        bad = ~np.isfinite(s) | (s < 0 if table in ['returns','promotions'] else s <= 0)
        if table=='promotions': bad |= s > 100
        check(table, 'invalid_'+col, bad.sum(), len(s), 'Stop if present: invalid numeric domain')
        assert not bad.any(), (table,col)
        q1, q3 = s.quantile([.25,.75])
        check(table, 'iqr_outlier_'+col, ((s<q1-1.5*(q3-q1)) | (s>q3+1.5*(q3-q1))).sum(), len(s), 'Review only; do not delete legitimate extremes')
for table, col in [('orders','order_date'),('customers','signup_date')]:
    s = pd.to_datetime(data[table][col], format='%Y-%m-%d', errors='coerce')
    check(table, 'invalid_'+col, s.isna().sum(), len(s), 'Stop if present: invalid date')
    assert s.notna().all()
    data[table][col] = s
for table, col in [('customers','city'),('stores','city'),('suppliers','country'),('categories','category_name'),('shipments','status')]:
    s = data[table][col]
    variants = pd.DataFrame({'raw':s,'normalized':s.str.casefold()}).groupby('normalized').raw.nunique()
    check(table, 'case_variants_'+col, variants.gt(1).sum(), len(variants), 'Review category variants; retain source labels')
    save(s.value_counts().rename_axis(col).reset_index(name='rows'), table+'_'+col, True)
before = data['shipments']['status'].copy()
data['shipments']['status'] = before.str.lower()
transformations.append(dict(table='shipments',transformation='lowercase status',changed=int((before!=data['shipments']['status']).sum())))
assert data['shipments']['status'].isin(['shipped','delivered','late']).all()
save(pd.DataFrame(manifest), 'source_manifest', True)
save(pd.DataFrame(profiles), 'column_profile', True)
save(pd.DataFrame(transformations), 'transformations', True)

orders, items, customers, products, returns = [data[t].copy() for t in ['orders','order_items','customers','products','returns']]
items['item_sales'] = items.qty * items.price
refunds = returns.groupby('order_item_id').agg(refund_amount=('refund','sum'),return_records=('return_id','size')).reset_index()
lines = items.merge(refunds, on='order_item_id', how='left', validate='one_to_one')
lines[['refund_amount','return_records']] = lines[['refund_amount','return_records']].fillna(0).astype('int64')
lines['returned_item'] = lines.return_records.gt(0).astype(int)
lines['refund_exceeds_sales'] = lines.refund_amount.gt(lines.item_sales).astype(int)
lines = lines.merge(products.rename(columns={'price':'catalog_price'}), on='product_id', validate='many_to_one')
lines = lines.merge(data['categories'], on='category_id', validate='many_to_one')
lines = lines.merge(orders, on='order_id', validate='many_to_one')
line_totals = lines.groupby('order_id').agg(item_sales=('item_sales','sum'),units=('qty','sum'),
    item_count=('order_item_id','size'),refund_amount=('refund_amount','sum'),returned_items=('returned_item','sum'),
    refund_excess_items=('refund_exceeds_sales','sum')).reset_index()
pay = data['payments'].groupby('order_id').agg(payment_amount=('amount','sum'),payment_records=('payment_id','size')).reset_index()
ship = data['shipments'].assign(late=lambda x:x.status.eq('late').astype(int)).groupby('order_id').agg(shipment_records=('shipment_id','size'),late_shipments=('late','sum')).reset_index()
fact = orders.merge(line_totals, on='order_id', how='left', validate='one_to_one').merge(pay,on='order_id',how='left',validate='one_to_one').merge(ship,on='order_id',how='left',validate='one_to_one')
for col in line_totals.columns.drop('order_id'): fact[col]=fact[col].fillna(0).astype('int64')
fact['has_items']=fact.item_count.gt(0).astype(int)
fact['has_return']=fact.returned_items.gt(0).astype(int)
fact = fact.merge(customers.rename(columns={'city':'customer_city'}),on='customer_id',validate='many_to_one')
fact = fact.merge(data['stores'].rename(columns={'city':'store_city'}),on='store_id',validate='many_to_one')
fact = fact.merge(data['promotions'],on='promotion_id',validate='many_to_one')
fact['before_signup'] = fact.order_date.lt(fact.signup_date).astype(int)
fact['payment_gap'] = fact.item_sales - fact.payment_amount
fact['discounted_sales_scenario'] = fact.item_sales * (1 - fact.discount / 100)
fact['month'] = fact.order_date.dt.strftime('%Y-%m')
fact['year'] = fact.order_date.dt.year
check('orders','without_items', fact.has_items.eq(0).sum(),len(fact),'Retain headers; exclude from sales-backed AOV denominator')
check('orders','before_signup',fact.before_signup.sum(),len(fact),'Retain sales; do not use signup for cohorts or tenure')
check('orders','payment_differs_from_item_sales',fact.payment_gap.abs().gt(.01).sum(),len(fact),'Keep payments separate from item sales')
check('orders','payment_differs_from_discount_scenario',(fact.discounted_sales_scenario-fact.payment_amount).abs().gt(.01).sum(),len(fact),'Do not apply promotion discount to sales without definition')
check('order_items','catalog_price_differs',lines.price.ne(lines.catalog_price).sum(),len(lines),'Use transaction price; no inferred discount from catalog price')
check('returns','repeated_item_reference',returns.order_item_id.duplicated().sum(),len(returns),'Keep distinct return IDs; aggregate before joining')
check('order_items','cumulative_refund_exceeds_sales',lines.refund_exceeds_sales.sum(),len(lines),'Flag and retain refunds; withhold verified net revenue')
for table in ['payments','shipments']:
    counts=data[table].groupby('order_id').size()
    check(table,'multiple_records_per_order',counts.gt(1).sum(),len(orders),'Aggregate each fact before joining')
    check('orders','without_'+table,(~orders.order_id.isin(counts.index)).sum(),len(orders),'Do not infer missing records are zero')
save(pd.DataFrame(checks),'checks',True)
save(fact.loc[fact.has_items.eq(0),['order_id','customer_id','order_date','payment_amount']], 'orders_without_items',True)
save(fact.loc[fact.before_signup.eq(1),['order_id','customer_id','order_date','signup_date']], 'orders_before_signup',True)
save(lines.loc[lines.refund_exceeds_sales.eq(1),['order_item_id','order_id','item_sales','refund_amount','return_records']], 'excess_refunds',True)
save(fact[['order_id','has_items','item_sales','payment_amount','payment_gap','discount','discounted_sales_scenario']], 'payment_reconciliation',True)

def order_summary(keys):
    a=fact.groupby(keys,dropna=False).agg(order_headers=('order_id','size'),sales_backed_orders=('has_items','sum'),
        item_sales=('item_sales','sum'),units=('units','sum'),ordering_customers=('customer_id','nunique'),
        returned_orders=('has_return','sum'),refund_amount=('refund_amount','sum'),payments=('payment_amount','sum')).reset_index()
    a['aov_sales_backed']=a.item_sales/a.sales_backed_orders.replace(0,np.nan)
    a['order_return_rate']=a.returned_orders/a.sales_backed_orders.replace(0,np.nan)
    a['sales_share']=a.item_sales/fact.item_sales.sum()
    return a
monthly=order_summary('month')
monthly['complete_calendar_month']=monthly.month.lt(fact.month.max()) | (fact.order_date.max()==fact.order_date.max()+pd.offsets.MonthEnd(0))
monthly['yoy_sales_change']=monthly.item_sales.pct_change(12)
monthly.loc[~monthly.complete_calendar_month,'yoy_sales_change']=np.nan
annual=order_summary('year')
annual['complete_calendar_year']=annual.year.lt(fact.year.max()) | ((fact.order_date.max().month==12) & (fact.order_date.max().day==31))
annual['yoy_sales_change']=annual.item_sales.pct_change()
annual.loc[~annual.complete_calendar_year,'yoy_sales_change']=np.nan
stores=order_summary(['store_id','store_city']).sort_values('item_sales',ascending=False)
promotions=order_summary(['promotion_id','discount']).sort_values('item_sales',ascending=False)
def item_summary(keys):
    a=lines.groupby(keys).agg(item_sales=('item_sales','sum'),units=('qty','sum'),sold_items=('order_item_id','size'),
        returned_items=('returned_item','sum'),refund_amount=('refund_amount','sum'),excess_refund_items=('refund_exceeds_sales','sum'),
        orders=('order_id','nunique')).reset_index()
    a['item_return_rate']=a.returned_items/a.sold_items
    a['sales_share']=a.item_sales/lines.item_sales.sum()
    return a.sort_values('item_sales',ascending=False)
categories=item_summary(['category_id','category_name'])
product_summary=item_summary(['product_id','category_name'])
customer_summary=fact.groupby('customer_id').agg(order_headers=('order_id','size'),sales_backed_orders=('has_items','sum'),
    item_sales=('item_sales','sum'),refund_amount=('refund_amount','sum'),last_order=('order_date','max')).reset_index()
last_sale=fact[fact.has_items.eq(1)].groupby('customer_id').order_date.max()
customer_summary['last_sale']=customer_summary.customer_id.map(last_sale)
snapshot=fact.order_date.max()+pd.Timedelta(days=1)
customer_summary['recency_days']=(snapshot-customer_summary.last_sale).dt.days
customer_summary['segment']=np.select([customer_summary.sales_backed_orders.eq(0),customer_summary.sales_backed_orders.eq(1)],['No item-backed order','One item-backed order'],default='Repeat item-backed buyer')
segments=customer_summary.groupby('segment').agg(customers=('customer_id','size'),item_sales=('item_sales','sum'),sales_backed_orders=('sales_backed_orders','sum')).reset_index()
segments['sales_share']=segments.item_sales/lines.item_sales.sum()
top_count=math.ceil(customer_summary.sales_backed_orders.gt(0).sum()*.1)
top_customers=customer_summary[customer_summary.sales_backed_orders.gt(0)].sort_values(['item_sales','customer_id'],ascending=[False,True]).head(top_count)
shipping=data['shipments'].groupby('status').size().rename('shipments').reset_index()
shipping['share']=shipping.shipments/shipping.shipments.sum()
for name, df in [('monthly_sales',monthly),('annual_sales',annual),('category_performance',categories),('product_performance',product_summary),
                 ('store_performance',stores),('customer_summary',customer_summary),('customer_segments',segments),('top_customers',top_customers),
                 ('promotion_performance',promotions),('shipment_status',shipping),('city_performance',order_summary('store_city')),
                 ('fact_orders',fact),('fact_items',lines)]: save(df,name)

kpi=dict(item_sales=int(lines.item_sales.sum()),order_headers=len(orders),sales_backed_orders=int(fact.has_items.sum()),
    ordering_customers=int(orders.customer_id.nunique()),sales_backed_customers=int(customer_summary.sales_backed_orders.gt(0).sum()),
    registered_customers=len(customers),units=int(items.qty.sum()),line_items=len(items),
    payments=int(data['payments'].amount.sum()),refunds=int(returns.refund.sum()),
    return_records=len(returns),returned_items=int(lines.returned_item.sum()),returned_orders=int(fact.has_return.sum()),
    repeat_buyers=int(customer_summary.sales_backed_orders.ge(2).sum()),
    top_decile_customer_count=top_count,top_decile_sales_share=float(top_customers.item_sales.sum()/lines.item_sales.sum()),
    avg_promotion_discount_raw=float(fact.discount.mean()),first_order=str(fact.order_date.min().date()),last_order=str(fact.order_date.max().date()),
    snapshot=str(snapshot.date()),refund_excess_value=int((lines.refund_amount-lines.item_sales).clip(lower=0).sum()),
    transaction_catalog_correlation=float(lines.price.corr(lines.catalog_price)),
    payment_sales_correlation=float(fact.item_sales.corr(fact.payment_amount)))
kpi.update(aov=kpi['item_sales']/kpi['sales_backed_orders'],sales_per_order_header=kpi['item_sales']/kpi['order_headers'],
           sales_per_customer=kpi['item_sales']/kpi['sales_backed_customers'],
           item_return_rate=kpi['returned_items']/kpi['line_items'],order_return_rate=kpi['returned_orders']/kpi['sales_backed_orders'],
           repeat_rate=kpi['repeat_buyers']/kpi['sales_backed_customers'],
           sales_less_recorded_refunds=kpi['item_sales']-kpi['refunds'])
(OUT/'kpis.json').write_text(json.dumps(kpi,indent=2,default=scalar)+'\n')

# Independent SQL execution on the prepared source. Aggregate facts at their own grain.
with sqlite3.connect(OUT/'retail_analysis.sqlite') as db:
    for name, df in data.items():
        df.to_sql(name,db,index=False,if_exists='replace')
        db.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS ix_{name}_pk ON {name}({KEYS[name]})')
    for child,col,parent in FKS:
        db.execute(f'CREATE INDEX IF NOT EXISTS ix_{child}_{col} ON {child}({col})')
    quality_sql=(ROOT/'sql/01b_data_quality.sql').read_text()
    quality_queries='\n'.join(line.split('--',1)[0] for line in quality_sql.splitlines()).split(';')
    for n,q in enumerate(quality_queries):
        if 'SELECT' in q.upper():
            save(pd.read_sql_query(q,db),f'sql_quality_{n+1:02}',True)
    db.executescript((ROOT/'sql/02_data_cleaning.sql').read_text())
    sql_text=(ROOT/'sql/03_business_analysis.sql').read_text()
    queries='\n'.join(line.split('--',1)[0] for line in sql_text.splitlines()).split(';')
    for n,q in enumerate(queries):
        if 'SELECT' in q.upper():
            result=pd.read_sql_query(q,db)
            save(result,f'sql_result_{n+1:02}')
            if n==1:
                assert result.item_sales.to_list()==monthly.item_sales.to_list()
                assert result.sales_backed_orders.to_list()==monthly.sales_backed_orders.to_list()
            if n==2:
                actual=result.set_index('category_id').sort_index()
                expected=categories.set_index('category_id').sort_index()
                for col in ['item_sales','units','sold_items','returned_items']:
                    assert actual[col].to_list()==expected[col].to_list(),col
            if n==4:
                assert int(result.iloc[0].buyers)==kpi['sales_backed_customers']
                assert int(result.iloc[0].repeat_buyers)==kpi['repeat_buyers']
    sql_kpi=pd.read_sql_query('SELECT SUM(item_sales) sales, SUM(has_items) orders, SUM(refund_amount) refunds FROM analytics_orders',db).iloc[0]
    assert int(sql_kpi.sales)==kpi['item_sales']
    assert int(sql_kpi.orders)==kpi['sales_backed_orders']
    assert int(sql_kpi.refunds)==kpi['refunds']
assert len(fact)==len(orders) and fact.order_id.is_unique
assert len(lines)==len(items) and lines.order_item_id.is_unique
assert lines.refund_amount.sum()==returns.refund.sum()
for result in [monthly,annual,stores,categories,product_summary,customer_summary,promotions]:
    assert result.item_sales.sum()==kpi['item_sales']
assert kpi['returned_items']==returns.order_item_id.nunique()
assert int(lines.loc[lines.returned_item.eq(1),'order_id'].nunique())==kpi['returned_orders']
assert fact.payment_amount.sum()==data['payments'].amount.sum()
(OUT/'validation.json').write_text(json.dumps({'status':'passed','checks':['unique fact grains','no join fanout','sales rollups reconcile','refunds reconcile','payments reconcile','distinct returns reconcile','independent SQL sales, order and refund totals'],'sql_engine':'SQLite','mysql_execution':'Not run; shared SQL uses portable syntax'},indent=2)+'\n')
print(json.dumps(kpi,indent=2,default=scalar))
print('Validation passed. Outputs:',OUT)
