# Power BI model and dashboard build guide

The completed visual report is `reports/retail_analysis.html`. This folder provides a model specification and DAX for a native Power BI version; a `.pbix` has not been created or validated.

## Import and model

Import `outputs/tables/fact_orders.csv` as **FactOrders** and `fact_items.csv` as **FactItems**. Set identifiers, quantities, flags, and amounts to whole numbers, discount to decimal, and order dates to Date. Use Decimal Number for scenario amounts. The original values use integer currency units; do not apply a currency symbol without confirming it.

Create **DimDate** from the minimum through maximum order date. Mark it as the date table. Add Year and YearMonth, with YearMonth sorted chronologically. Import **DimStore**, **DimCustomer**, **DimProduct**, and **DimCategory** from the corresponding raw CSVs.

Use single-direction relationships:

- DimDate[Date] 1 → many FactOrders[order_date]
- DimStore[store_id] 1 → many FactOrders[store_id]
- DimCustomer[customer_id] 1 → many FactOrders[customer_id]
- FactOrders[order_id] 1 → many FactItems[order_id]
- DimCategory[category_id] 1 → many DimProduct[category_id]
- DimProduct[product_id] 1 → many FactItems[product_id]

Keep shipment status summaries disconnected or import raw shipments with a single-direction FactOrders → Shipments relationship. Do not also relate DimDate or DimStore directly to FactItems: this would create an additional filter path. Avoid bidirectional relationships.

Sales measures use FactItems so product/category filters work. Order-header and payment measures use FactOrders and do **not** respond to product/category filters. Keep them off product-filtered pages. AOV uses distinct item order IDs, so it means sales per order containing selected products when filtered by product/category. Label that context explicitly.

## Pages

1. **Sales overview:** recorded item sales, item-backed orders, AOV, units; monthly line chart through Dec 2023; category share and store sales bars. Date/store slicers. Clearly state that Jan 2024 is partial if selected.
2. **Customers:** sales-backed customers, repeat-buyer rate, sales per customer; customer table with sales, order count, recency. Date/store slicers. Repeat rate recalculates within the selected period, unlike full-history segmentation CSVs.
3. **Products and returns:** category/product sales, sold items, returned items, returned-item rate. Show exposure beside rate and minimum-volume filters. Product/category slicers. Refunds follow sale date, not refund date.
4. **Data quality:** headers without items, orders before signup, payment gap, excessive-refund items, and recorded status distribution. Include source limitations.

## Validation before publishing

Compare unfiltered results with `outputs/kpis.json`. Expect sales 3,827,746,136; sales-backed orders 259,233; AOV 14,765.6592; returned-item rate 4.87517%; returned-order rate 10.72086%. Confirm a store and date selection agree with exported summaries. Check product filters affect item-based sales and order denominators consistently. Test that totals count distinct customers/orders rather than summing category subtotals.

Use consistent labels, two-decimal rates, full tooltips, accessible contrast, and no default currency symbol. DAX in `measures.dax` is provided for implementation and has not been executed in Power BI.
