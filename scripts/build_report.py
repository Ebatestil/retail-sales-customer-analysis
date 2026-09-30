"""Create a self-contained HTML report, Markdown report, charts and data dictionary."""
from pathlib import Path
import base64
import json
import re
from html import escape
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'
REPORT=ROOT/'reports'
REPORT.mkdir(exist_ok=True)
CHARTS=ROOT/'screenshots'
CHARTS.mkdir(exist_ok=True)
font_css=''.join(
    "@font-face{font-family:'Poppins';font-style:normal;font-weight:"
    +str(weight)+";font-display:swap;src:url(data:font/ttf;base64,"
    +base64.b64encode((ROOT/'assets/fonts'/f'Poppins-{name}.ttf').read_bytes()).decode('ascii')
    +") format('truetype');}"
    for weight,name in [(400,'Regular'),(600,'SemiBold'),(700,'Bold')]
)
font_style='<style>'+font_css+'</style>'
k=json.loads((OUT/'kpis.json').read_text())
validation=json.loads((OUT/'validation.json').read_text())
assert validation['status']=='passed', 'Run the successful analysis before publishing the report'
def read(name): return pd.read_csv(OUT/'tables'/f'{name}.csv')
annual,monthly,categories,stores,segments,shipping,products=[read(n) for n in ['annual_sales','monthly_sales','category_performance','store_performance','customer_segments','shipment_status','product_performance']]
quality=pd.read_csv(OUT/'quality/checks.csv')
manifest=pd.read_csv(OUT/'quality/source_manifest.csv')
def issue(rule): return int(quality.loc[quality.rule.eq(rule),'affected'].iloc[0])
def n(v): return f'{v:,.0f}'
def pct(v): return f'{v:.2%}'
def money(v): return f'{v:,.2f}'
def md_table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def svg_base(title, subtitle, content, height=400):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" role="img" aria-label="{escape(title)}"><title>{escape(title)}</title><desc>{escape(subtitle)}</desc>{font_style}<rect width="960" height="{height}" fill="#fff" rx="14"/><g font-family="Poppins,Arial,sans-serif" fill="#182b49"><text x="28" y="36" font-size="21" font-weight="600">{escape(title)}</text><text x="28" y="60" font-size="13" fill="#52637a">{escape(subtitle)}</text>{content}</g></svg>'''
def bars(title,subtitle,labels,values,formatter,color='#3563a5'):
    h=115+len(labels)*38
    max_v=max(values)*1.2
    s=''
    for i,(label,value) in enumerate(zip(labels,values)):
        y=89+i*38
        w=value/max_v*640
        s+=f'<text x="26" y="{y+18}" font-size="14">{escape(str(label))}</text><rect x="172" y="{y}" width="{w:.2f}" height="25" rx="3" fill="{color}"><title>{escape(str(label))}: {escape(formatter(value))}</title></rect><text x="{184+w:.2f}" y="{y+18}" font-size="14">{escape(formatter(value))}</text>'
    return svg_base(title,subtitle,s,h)
def trend():
    df=monthly.loc[monthly.complete_calendar_month.eq(True)]
    vals=df.item_sales.to_list(); bottom=335; top=100; left=85; right=914
    ymax=100_000_000
    s=''
    for v in range(0,100_000_001,25_000_000):
        y=bottom-v/ymax*(bottom-top)
        s+=f'<line x1="{left}" x2="{right}" y1="{y}" y2="{y}" stroke="#e3e9f0"/><text x="72" y="{y+5}" text-anchor="end" font-size="12">{v/1e6:.0f}M</text>'
    points=[(left+i/(len(vals)-1)*(right-left),bottom-v/ymax*(bottom-top)) for i,v in enumerate(vals)]
    poly=' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
    s+=f'<polygon points="{left},{bottom} {poly} {right},{bottom}" fill="#eaf0fa"/><polyline points="{poly}" fill="none" stroke="#3563a5" stroke-width="3"/>'
    for i,((x,y),month) in enumerate(zip(points,df.month)):
        s+=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="#3563a5"><title>{month}: {n(vals[i])} CU</title></circle>'
        if i%12==0 or i==len(vals)-1:
            s+=f'<text x="{x}" y="366" text-anchor="middle" font-size="13">{month}</text>'
    return svg_base('Monthly sales show a stable baseline','Recorded item sales, CU millions. January 2024 excluded because it contains only one day.',s)
charts={
 'monthly_sales':trend(),
 'category_sales':bars('No single category dominates sales','Top 8 of 30 categories. All-period share of recorded item sales.',categories.head(8).category_name.to_list(),categories.head(8).sales_share.to_list(),pct),
 'store_sales':bars('Leading stores have similar sales totals','Top 6 of 100 stores. CU millions. Sales alone do not establish efficiency.',[f'Store {r.store_id}' for r in stores.head(6).itertuples()],stores.head(6).item_sales.to_list(),lambda v:f'{v/1e6:.2f}M'),
 'shipment_status':bars('One third of shipments carry a late label','Recorded status distribution. Delivery dates and promised dates are unavailable.',shipping.status.to_list(),shipping.share.to_list(),pct),
 'customer_concentration':bars('Top 10% of buyers contribute about 21% of sales','Customers ranked by observed item sales over the full period.', ['Top 10% of buyers','Remaining buyers'],[k['top_decile_sales_share'],1-k['top_decile_sales_share']],pct),
 'quality_exceptions':bars('Business-rule exceptions affect interpretation','Percent of 300,000 order headers. Checks overlap and must not be added.', ['Payment mismatch','Before signup','No items'],[issue('payment_differs_from_item_sales')/k['order_headers'],issue('before_signup')/k['order_headers'],issue('without_items')/k['order_headers']],pct,'#ae6136')
}
for name,svg in charts.items(): (CHARTS/f'{name}.svg').write_text(svg,encoding='utf-8')
# Standalone charts embed their fonts. Inline charts reuse the report's font faces.
charts={name:svg.replace(font_style,'') for name,svg in charts.items()}
top=categories.iloc[0]; best=stores.iloc[0]; product=products.iloc[0]
full_years=annual[annual.complete_calendar_year.eq(True)]
y2023=annual.loc[annual.year.eq(2023)].iloc[0]
return_candidates=products[products.sold_items.ge(50)].sort_values(['item_return_rate','sold_items','product_id'],ascending=[False,False,True]).head(5)
return_candidates.to_csv(OUT/'tables/return_review_candidates.csv',index=False)
high=return_candidates.iloc[0]
sections=[]
def add(title,text,chart=None): sections.append((title,text.strip(),chart))
add('Executive Summary',f'''
Recorded item sales total **{n(k['item_sales'])} CU** across **{n(k['sales_backed_orders'])} orders with items** from {k['first_order']} to {k['last_order']}. This is an analytical sales measure based on quantity times transaction price. Its accounting treatment and currency are undocumented.

- Full-year 2023 sales were **{n(y2023.item_sales)} CU**, changing **{pct(y2023.yoy_sales_change)}** from 2022. The four complete years show a stable baseline.
- **{top.category_name}** leads with **{pct(top.sales_share)}** of sales. Its lead is small within a broad category mix.
- **{pct(k['repeat_rate'])}** of customers with an item-backed purchase bought at least twice during the full period. The top 10% by observed sales contribute **{pct(k['top_decile_sales_share'])}** of sales.
- The most important prerequisite for business use is reconciliation: **{n(issue('without_items'))}** orders lack items, **{n(issue('before_signup'))}** predate signup, and **{n(issue('cumulative_refund_exceeds_sales'))}** items have refunds above recorded sales.

Recommended sequence: resolve transaction definitions and exceptions, establish the sales baseline, then test customer and assortment actions with additional operational data.
''')
add('Business Questions','''
1. How are sales and order values changing over time?
2. Which categories, products, and stores contribute most?
3. How many customers purchase repeatedly, and how concentrated are sales?
4. Which products merit a returns review?
5. Do promotion values explain transaction prices or payments?
6. What can shipment records tell us about fulfillment?

The intended stakeholder is a retail manager deciding where to investigate and what to test. The project demonstrates SQL, data profiling, analytical modeling, KPI design, visualization, and evidence-based communication.
''')
add('Dataset Overview',f'''
The supplied dataset has **{n(manifest.rows.sum())} rows across 12 tables**, including 300,000 order headers and 600,000 item rows. The order-date range is **{k['first_order']} to {k['last_order']}**. The final date contributes only one day to January 2024. Customer signup dates run from 2019-01-01 to 2024-01-01.

{md_table(['Table','Rows','Grain'],[(r.file.removeprefix('data/').removesuffix('.csv'),n(r.rows),{'categories':'Category','customers':'Customer','employees':'Employee','order_items':'Order item','orders':'Order header','payments':'Payment record','products':'Product','promotions':'Promotion','returns':'Return record','shipments':'Shipment record','stores':'Store','suppliers':'Supplier'}[r.file.removeprefix('data/').removesuffix('.csv')]) for r in manifest.itertuples()])}

The README identifies Kaggle as the source, but the exact URL and license are missing. The labels and distributions suggest a generated dataset; this is an inference, not verified provenance. See the [data dictionary](../docs/data_dictionary.md) for columns and relationships and the [source manifest](../outputs/quality/source_manifest.csv) for file hashes.
''')
add('Data Quality and Cleaning',f'''
All supplied columns were checked for missing/blank values, all primary keys for duplicates, and all 11 foreign-key relationships for unmatched records. These structural checks found no exceptions. Valid date formats and tested numeric domains also passed. No text values needed trimming or shipment case correction in this snapshot.

{md_table(['Finding','Affected','Treatment'],[
('Order headers without items',f"{n(issue('without_items'))} / 300,000 (13.59%)",'Retain and flag; exclude from primary AOV denominator'),
('Orders before customer signup',f"{n(issue('before_signup'))} / 300,000 (40.01%)",'Retain sales; withhold signup cohorts'),
('Payment differs from item sales',f"{n(issue('payment_differs_from_item_sales'))} / 300,000",'Report payments separately'),
('Transaction price differs from catalog',f"{n(issue('catalog_price_differs'))} / 600,000",'Use recorded transaction price'),
('Return records beyond first per item',n(issue('repeated_item_reference')),'Aggregate by item before joining; preserve return IDs'),
('Items with cumulative excessive refunds',f"{n(issue('cumulative_refund_exceeds_sales'))} / {n(k['returned_items'])} returned items",'Retain and flag; withhold verified net revenue')])}

The excessive-refund items account for **{pct(issue('cumulative_refund_exceeds_sales')/k['returned_items'])}** of returned items; their aggregate refund excess is **{n(k['refund_excess_value'])} CU**. Repeated item references are not automatically duplicate returns because the return IDs differ.

Preparation preserves every source row, parses dates, derives sales and issue flags, and aggregates each fact before joining. The SQL and Python pipelines validate unique output grains and reconciled sums. [Full audit](../outputs/quality/checks.csv) and [methodology](../docs/methodology.md) provide the evidence and decisions.
''','quality_exceptions')
add('KPI Summary',f'''
Headline metrics include all observed dates. Sales-backed means an order has at least one item row. Amounts use CU because currency is unconfirmed.

{md_table(['KPI','Value','Definition'],[
('Recorded item sales',n(k['item_sales'])+' CU','SUM(qty × transaction price)'),
('Order headers',n(k['order_headers']),'All order IDs'),
('Sales-backed orders',n(k['sales_backed_orders']),'Order IDs represented in items'),
('Sales-backed AOV',money(k['aov'])+' CU','Sales / sales-backed orders'),
('Ordering customers',n(k['ordering_customers']),'Customers in headers'),
('Sales-backed customers',n(k['sales_backed_customers']),'Customers with item-backed orders'),
('Units sold',n(k['units']),'Sum of quantities'),
('Returned-item rate',pct(k['item_return_rate']),'29,251 distinct returned item IDs / 600,000 items'),
('Returned-order rate',pct(k['order_return_rate']),'27,792 returned orders / 259,233 sales-backed orders'),
('Repeat-buyer rate',pct(k['repeat_rate']),'At least 2 item-backed orders / sales-backed buyers'),
('Sales per customer',money(k['sales_per_customer'])+' CU','Sales / sales-backed customers'),
('Recorded payments',n(k['payments'])+' CU','Sum of payment records'),
('Recorded refunds',n(k['refunds'])+' CU','Sum of return records')])}

Using all order headers would produce **{money(k['sales_per_order_header'])} CU** per header. This differs from the primary AOV because 13.59% of headers have no items. The arithmetic result of sales less recorded refunds is **{n(k['sales_less_recorded_refunds'])} CU**, but it is not verified net revenue. Profit, margin, realized average discount, and unit return rate are unavailable.
''')
add('Sales Analysis',f'''
{md_table(['Year','Recorded item sales (CU)','Sales-backed orders','Year-over-year change'],[(int(r.year),n(r.item_sales),n(r.sales_backed_orders),'Baseline' if pd.isna(r.yoy_sales_change) else pct(r.yoy_sales_change)) for r in full_years.itertuples()])}

Full-year sales range from **{n(full_years.item_sales.min())} to {n(full_years.item_sales.max())} CU**. A flat four-year pattern supports a stable historical baseline; it does not establish a growth forecast. Monthly totals reflect different numbers of days as well as transaction volume, so these charts alone do not prove seasonal demand.

The partial January 2024 extract contains **195 order headers, 175 sales-backed orders, and 2,477,460 CU** of sales. Comparing it with a full month or year would produce a misleading decline. [Monthly detail](../outputs/tables/monthly_sales.csv) includes completeness flags and like-month growth for complete months.
''','monthly_sales')
add('Customer Analysis',f'''
Of 50,000 registered customers, **{n(k['ordering_customers'])}** appear in order headers and **{n(k['sales_backed_customers'])}** have at least one item-backed purchase. There are **114 customers with no order header** and **135 with headers but no item-backed purchase**.

{md_table(['Observed customer group','Customers','Recorded item sales (CU)'],[(r.segment,n(r.customers),n(r.item_sales)) for r in segments.itertuples()])}

Repeat buyers contribute **{pct(segments.loc[segments.segment.eq('Repeat item-backed buyer'),'sales_share'].iloc[0])}** of sales. Their **{pct(k['repeat_rate'])}** repeat rate covers approximately four years, so it should not be presented as annual retention or proof of loyalty.

The top **{n(k['top_decile_customer_count'])}** sales-backed customers, approximately 10%, account for **{pct(k['top_decile_sales_share'])}** of sales. This gives a defined group for a retention test without claiming an 80/20 concentration. [Customer summaries](../outputs/tables/customer_summary.csv) include frequency, sales and recency as of **{k['snapshot']}**. Signup dates are excluded from segmentation because 40.01% of orders predate signup.
''','customer_concentration')
add('Product and Category Analysis',f'''
**{top.category_name}** generates **{n(top.item_sales)} CU**, or **{pct(top.sales_share)}** of all sales. Across the 30 categories, shares range from **{pct(categories.sales_share.min())} to {pct(categories.sales_share.max())}**. This is a broad mix, with no dominant category in the extract.

The highest-sales product is **Product {int(product.product_id)}** in **{product.category_name}**, with **{n(product.item_sales)} CU** across **{int(product.sold_items)} item rows**. Its contribution is just **{pct(product.sales_share)}** of total sales. A ranking alone is insufficient evidence for a major inventory shift.

Keep the anonymous source labels until a merchandise mapping is supplied. Assess units and return exposure alongside sales. [Category detail](../outputs/tables/category_performance.csv) and [product detail](../outputs/tables/product_performance.csv) contain the full rankings.
''','category_sales')
add('Store Analysis',f'''
**Store {int(best.store_id)} in {best.store_city}** leads with **{n(best.item_sales)} CU**, representing **{pct(best.sales_share)}** of total sales. It has **{n(best.sales_backed_orders)}** item-backed orders and **{money(best.aov_sales_backed)} CU** AOV.

Across 100 stores, sales range from **{n(stores.item_sales.min())} to {n(stores.item_sales.max())} CU**. The top store is only **{pct(stores.item_sales.max()/stores.item_sales.min()-1)}** above the lowest by observed sales. Small ranking differences should prompt a closer comparison of order volume, AOV, returns and store context before resources are reassigned.

Store size, opening dates, footfall and operating costs are absent, so revenue rank does not measure productivity or profitability. [Store detail](../outputs/tables/store_performance.csv) supports further review.
''','store_sales')
add('Returns and Shipping Analysis',f'''
The **{n(k['return_records'])} return records** reference **{n(k['returned_items'])} distinct item rows** across **{n(k['returned_orders'])} orders**. The returned-item rate is **{pct(k['item_return_rate'])}** and returned-order rate is **{pct(k['order_return_rate'])}**. Simply dividing return records by orders would mix grains and overcount repeat return references.

The following products are review candidates among those with at least 50 sold item rows. The threshold is a transparent screening choice, not statistical significance.

{md_table(['Product','Sold items','Returned items','Returned-item rate'],[(int(r.product_id),int(r.sold_items),int(r.returned_items),pct(r.item_return_rate)) for r in return_candidates.itertuples()])}

Product **{int(high.product_id)}** has the highest observed rate in this screen, **{pct(high.item_return_rate)}** across **{int(high.sold_items)}** sold item rows. Small samples and screening 10,000 products can produce extreme rates by chance. Inspect return reasons and additional periods before inferring defects.

**99,855 of 300,000 shipments (33.29%)** are labeled late. This is a status-label share, not a validated on-time-delivery KPI. There are no event timestamps, promised dates, carriers or delivery durations. Returns have no event date, so refund amounts grouped by order date reflect the original sale period, not refund cash flow.
''','shipment_status')
add('Promotions and Revenue Reconciliation',f'''
All 300,000 orders reference one of 50 promotions. Their order-weighted average `discount` value is **{k['avg_promotion_discount_raw']:.4f}**, but its unit and realized application are undocumented.

Recorded payments total **{n(k['payments'])} CU**, which is **{n(k['item_sales']-k['payments'])} CU** below calculated item sales. Only **10 orders** match item sales within 0.01 CU. Applying an illustrative percentage discount to item sales produces **zero matching orders** at that tolerance.

Transaction price and catalog price have Pearson correlation **{k['transaction_catalog_correlation']:.4f}**; order item sales and recorded payments have correlation **{k['payment_sales_correlation']:.4f}**. These near-zero correlations reinforce the need for source definitions. They do not establish how the dataset was generated.

Use [payment reconciliation](../outputs/quality/payment_reconciliation.csv) to inspect specific orders. Keep promotion comparisons descriptive because there is no unpromoted control group, no campaign dates and no documented eligibility. Do not claim promotion lift or apply an additional discount to the headline sales measure.
''')
add('Key Insights',f'''
1. **The largest analytical risk is semantic consistency.** Clean keys and complete fields coexist with missing item records, incompatible signup dates and unreconciled monetary facts.
2. **Complete-year sales are stable.** The 2023 change of {pct(y2023.yoy_sales_change)} provides little evidence of sustained growth or decline.
3. **Sales are spread across categories and stores.** The largest category contributes {pct(top.sales_share)} and the largest store {pct(best.sales_share)}.
4. **Repeat purchasing is common over the full period.** The {pct(k['repeat_rate'])} rate is descriptive and should not be relabeled as annual retention.
5. **Return rates require a defined grain.** A {pct(k['item_return_rate'])} item rate and {pct(k['order_return_rate'])} order rate answer different questions.
''')
add('Recommendations','''
| Priority | Evidence | Proposed action | How to assess progress |
|---|---|---|---|
| 1 | 299,990 payment mismatches; 40,767 itemless headers | Ask the source owner for price, payment, tax, freight and order-state definitions; trace sample IDs | Reconciled-order share and unresolved itemless headers |
| 1 | 7,498 returned items have excessive cumulative refunds | Review return IDs against policy and original transactions before defining net revenue | Excess-refund cases with documented explanations or corrections |
| 1 | 120,020 orders predate signup | Validate signup semantics and date-generation rules | Documented resolution of signup inconsistencies |
| 2 | Top customer decile contributes 20.88% of sales | Design a retention test with a randomized holdout after customer data validation | Incremental repeat purchases and contribution after offer costs |
| 2 | Product return-rate outliers with limited samples | Review candidate products using reasons, quantities and subsequent-period evidence | Returned-item rate with exposure and confidence intervals |
| 2 | 33.29% of shipments labeled late | Add dispatch, promised and actual delivery timestamps and carrier data | Validated on-time-delivery rate and transit duration |
| 3 | Stable sales and broadly distributed contributions | Use complete-period sales as a baseline; test assortment changes on a limited scale | Comparable-period sales, stockouts and margin once cost data exist |

These are proposals for investigation and controlled tests. The extract does not support quantified profit improvements or a causal explanation for returns.
''')
add('Methodology and Limitations','''
The process follows business questions, source profiling, quality investigation, preparation, EDA, KPI definition, visualization, interpretation, recommendations and reporting. Original CSVs and exploration notes are preserved. Preparation uses explicit flags and aggregates facts before joins to prevent multiplication of sales and refunds.

Python assertions confirm unique grains, reconciled sales across each summary, payments/refunds against source totals, and distinct return counts. The preparation and business-analysis SQL execute in SQLite, and sales, order and refund totals agree with the pandas calculations. MySQL execution and native Power BI DAX execution have not been performed.

The exact dataset source, license, currency and business definitions remain unconfirmed. Profit/margin, payment-method analysis, delivery duration, return causes and realized discount are unavailable. January 2024 is partial. Refunds have no event dates, and signup inconsistencies prevent defensible acquisition cohorts. The results describe the supplied extract and should not be generalized to a real retailer without validation.

See the [methodology and KPI dictionary](../docs/methodology.md), [data dictionary](../docs/data_dictionary.md), [verification result](../outputs/validation.json), and [Power BI build guide](../powerbi/README.md). Rebuild with `python scripts/analyze.py` followed by `python scripts/build_report.py`.
''')

md='# Retail Sales & Customer Analytics\n\nSource period: 2020-01-01 to 2024-01-01. Amounts in unspecified currency units (CU).\n\n'
for title,text,chart in sections:
    md+=f'## {title}\n\n{text}\n\n'
    if chart: md+=f'![{title}](../screenshots/{chart}.svg)\n\n'
(REPORT/'final_report.md').write_text(md,encoding='utf-8')

def inline(s):
    s=escape(s)
    s=re.sub(r'\*\*(.*?)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'`(.*?)`',r'<code>\1</code>',s)
    return re.sub(r'\[(.*?)\]\((.*?)\)',r'<a href="\2">\1</a>',s)
def render_md(text):
    blocks=text.strip().split('\n\n'); parts=[]
    for block in blocks:
        lines=block.splitlines()
        if lines[0].startswith('|'):
            rows=[[c.strip() for c in line.strip('|').split('|')] for line in lines]
            parts.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+inline(c)+'</th>' for c in rows[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in row)+'</tr>' for row in rows[2:])+'</tbody></table></div>')
        elif all(line.startswith('- ') for line in lines): parts.append('<ul>'+''.join('<li>'+inline(line[2:])+'</li>' for line in lines)+'</ul>')
        elif all(re.match(r'^\d+\. ',line) for line in lines): parts.append('<ol>'+''.join('<li>'+inline(re.sub(r'^\d+\. ','',line))+'</li>' for line in lines)+'</ol>')
        else: parts.append('<p>'+inline(' '.join(lines))+'</p>')
    return ''.join(parts)
css='''*{box-sizing:border-box}body{margin:0;background:#f1f4f8;color:#243650;font:16px/1.65 "Segoe UI",Arial,sans-serif}header{background:#182b49;color:white;padding:52px max(24px,calc((100vw - 1160px)/2));}header p{color:#c4d0e2;max-width:860px}h1{font-size:42px;line-height:1.15;margin:12px 0 18px;letter-spacing:-1px}h2{font-size:26px;line-height:1.3;margin:0 0 24px;color:#182b49}a{color:#225aa0;text-underline-offset:3px}main{max-width:1208px;margin:auto;padding:28px 24px 60px}nav{display:flex;gap:10px 18px;flex-wrap:wrap;margin:0 0 26px;font-size:14px}section{background:white;border:1px solid #dbe2ec;border-radius:12px;padding:32px;margin-bottom:24px;scroll-margin-top:20px}p{margin:14px 0}li{margin:9px 0}strong{color:#182b49}header strong{color:white}.eyebrow{font-size:13px;letter-spacing:2px;text-transform:uppercase;color:#a8c5ed}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:0 0 28px}.card{background:white;border-top:4px solid #3563a5;padding:22px;border-radius:7px}.card b{font-size:30px;display:block;line-height:1.3;color:#182b49}.card span{font-size:13px;color:#53667d}.note{background:#fff5e9;color:#76431e;border-left:4px solid #ae6136;padding:16px 20px;margin:0 0 26px}.table-wrap{overflow-x:auto;margin:22px 0}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.5}th{text-align:left;background:#edf2f8;color:#182b49;padding:12px 14px}td{border-bottom:1px solid #e2e8f0;padding:11px 14px;vertical-align:top}svg{width:100%;height:auto;display:block;margin-top:22px;border:1px solid #e3e9f0;border-radius:12px}code{background:#edf2f8;padding:2px 5px;border-radius:4px;font-size:13px}footer{color:#53667d;font-size:13px}@media(max-width:700px){h1{font-size:32px}.cards{grid-template-columns:repeat(2,1fr)}section{padding:22px}main{padding:20px 12px}.card b{font-size:24px}}@media print{body{background:white;font-size:11px}header{padding:20px;background:white;color:#182b49}header p{color:#53667d}nav{display:none}section{border:0;padding:15px 0;break-inside:auto}h2,svg,table{break-inside:avoid}.cards{margin-top:10px}main{padding:0}.card b{font-size:24px}a{color:inherit}svg{max-height:330px}}'''
css=font_css+css.replace('"Segoe UI",Arial,sans-serif','"Poppins",Arial,sans-serif')
html=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retail Sales & Customer Analytics</title><style>{css}</style></head><body><header><div class="eyebrow">Data analyst portfolio</div><h1>Retail Sales &amp;<br>Customer Analytics</h1><p>Four years of retail transactions, examined from data quality to business decisions. Source period: January 2020 to January 1, 2024.</p></header><main>'
html+='<div class="cards">'+''.join(f'<div class="card"><span>{label}</span><b>{value}</b><span>{detail}</span></div>' for label,value,detail in [('Recorded item sales','3.828B','Unspecified currency units'),('Sales-backed orders',n(k['sales_backed_orders']),'Of 300,000 order headers'),('Sales-backed AOV',f"{k['aov']:,.0f}",'Currency units per order'),('Returned-item rate',pct(k['item_return_rate']),'Distinct returned item rows')])+'</div>'
html+='<div class="note"><strong>Interpretation matters.</strong> Sales are based on recorded items. Payments and refunds do not fully reconcile, and January 2024 is partial. Read the definitions before using these figures.</div>'
html+='<nav aria-label="Report sections">'+''.join(f'<a href="#section-{i}">{escape(t)}</a>' for i,(t,_,_) in enumerate(sections))+'</nav>'
for i,(title,text,chart) in enumerate(sections): html+=f'<section id="section-{i}"><h2>{escape(title)}</h2>{render_md(text)}'+(charts[chart] if chart else '')+'</section>'
html+='<footer>Reproducible from the 12 supplied CSV files. See the project README for build commands and source limitations.</footer></main></body></html>'
(REPORT/'retail_analysis.html').write_text(html,encoding='utf-8')

# Column meanings are interpretations of supplied names, not a source-authored dictionary.
profile=pd.read_csv(OUT/'quality/column_profile.csv')
meanings={'city':'Customer or store city as recorded','country':'Supplier country as recorded','signup_date':'Recorded customer signup date; chronology is inconsistent with many orders',
 'order_date':'Recorded order date','qty':'Number of units in the item row','price':'Recorded price; unit-price interpretation used for items, catalog price for products',
 'salary':'Recorded employee salary; pay period and currency unknown','discount':'Promotion discount field; units and application unknown','amount':'Recorded payment amount; does not reconcile with item sales',
 'refund':'Recorded refund amount; returned quantity and event date absent','status':'Recorded shipment status: delivered, shipped or late','category_name':'Anonymous category label'}
dictionary='# Data Dictionary and Relationships\n\nDefinitions below are inferred from field names and observed values. Source-authored business definitions are unavailable. Detailed raw profiles are in `outputs/quality/column_profile.csv`.\n\n'
for table,df in profile.groupby('table',sort=True):
    pk={'categories':'category_id','order_items':'order_item_id'}.get(table,table[:-1]+'_id')
    rows=[]
    for r in df.itertuples():
        meaning=meanings.get(r.column,'Identifier linking to the named entity')
        role='Primary key' if r.column==pk else ('Foreign key' if r.column.endswith('_id') else 'Attribute')
        typ='date (CSV text)' if r.column.endswith('_date') else ('integer' if 'int' in r.dtype else 'text')
        rows.append((r.column,typ,role,meaning))
    dictionary+=f'## {table}\n\n{int(df.iloc[0].rows):,} rows. Primary key: `{pk}`.\n\n'+md_table(['Column','Type','Role','Interpretation'],rows)+'\n\n'
dictionary+='''## Relationships

```mermaid
erDiagram
    customers ||--o{ orders : places
    stores ||--o{ orders : receives
    promotions ||--o{ orders : referenced_by
    orders ||--o{ order_items : contains
    orders ||--o{ payments : has
    orders ||--o{ shipments : has
    products ||--o{ order_items : sold_as
    categories ||--o{ products : classifies
    suppliers ||--o{ products : supplies
    order_items ||--o{ returns : referenced_by
    stores ||--o{ employees : employs
```

The diagram describes join directions and allows multiple child records. Observed payments and shipments are one per order in this snapshot. Some orders have no items. An order item may have multiple return records. All 11 foreign-key checks pass.
'''
(ROOT/'docs/data_dictionary.md').write_text(dictionary,encoding='utf-8')
print('Created reports/retail_analysis.html, reports/final_report.md, six SVG charts and docs/data_dictionary.md')
