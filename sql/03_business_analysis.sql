-- Execute after 02_data_cleaning.sql. Sales are in unspecified currency units.
-- Item sales are an analytical proxy, not verified accounting revenue.

-- 1. Core KPIs. Keep all headers and item-backed orders as separate populations.
SELECT SUM(item_sales) AS recorded_item_sales, COUNT(*) AS order_headers,
       SUM(has_items) AS sales_backed_orders,
       COUNT(DISTINCT CASE WHEN has_items = 1 THEN customer_id END) AS sales_backed_customers,
       SUM(units) AS units,
       1.0 * SUM(item_sales) / NULLIF(SUM(has_items), 0) AS sales_backed_aov,
       SUM(refund_amount) AS recorded_refunds,
       SUM(payment_amount) AS recorded_payments,
       1.0 * SUM(has_return) / NULLIF(SUM(has_items), 0) AS order_return_rate
FROM analytics_orders;

-- 2. Monthly sales. The final month is partial; omit it from trend comparisons.
SELECT SUBSTR(order_date,1,7) AS month, SUM(item_sales) AS item_sales,
       COUNT(*) AS order_headers, SUM(has_items) AS sales_backed_orders,
       1.0 * SUM(item_sales) / NULLIF(SUM(has_items),0) AS aov
FROM analytics_orders GROUP BY SUBSTR(order_date,1,7) ORDER BY month;

-- 3. Category sales and returned-line rate (a line may contain multiple units).
SELECT c.category_id, c.category_name, SUM(i.item_sales) AS item_sales,
       SUM(i.qty) AS units, COUNT(*) AS sold_items, SUM(i.returned_item) AS returned_items,
       1.0 * SUM(i.returned_item)/COUNT(*) AS item_return_rate,
       SUM(i.refund_amount) AS recorded_refunds
FROM analytics_items i JOIN products p ON i.product_id=p.product_id
JOIN categories c ON p.category_id=c.category_id
GROUP BY c.category_id,c.category_name ORDER BY item_sales DESC;

-- 4. Stores. Revenue alone does not measure profitability or operating efficiency.
SELECT s.store_id,s.city, SUM(o.item_sales) AS item_sales, SUM(o.has_items) AS sales_backed_orders,
       1.0 * SUM(o.item_sales)/NULLIF(SUM(o.has_items),0) AS aov,
       1.0 * SUM(o.has_return)/NULLIF(SUM(o.has_items),0) AS order_return_rate
FROM analytics_orders o JOIN stores s ON o.store_id=s.store_id
GROUP BY s.store_id,s.city ORDER BY item_sales DESC;

-- 5. Repeat buyers measured using orders that actually have items.
WITH customer_totals AS (
    SELECT customer_id, SUM(has_items) AS purchase_orders, SUM(item_sales) AS item_sales
    FROM analytics_orders GROUP BY customer_id
)
SELECT SUM(CASE WHEN purchase_orders>0 THEN 1 ELSE 0 END) AS buyers,
       SUM(CASE WHEN purchase_orders>1 THEN 1 ELSE 0 END) AS repeat_buyers,
       1.0*SUM(CASE WHEN purchase_orders>1 THEN 1 ELSE 0 END) /
       NULLIF(SUM(CASE WHEN purchase_orders>0 THEN 1 ELSE 0 END),0) AS repeat_rate
FROM customer_totals;

-- 6. Top customers by observed sales; no lifetime-value forecast.
SELECT customer_id, SUM(item_sales) AS item_sales, SUM(has_items) AS purchase_orders,
       MAX(CASE WHEN has_items=1 THEN order_date END) AS last_purchase
FROM analytics_orders GROUP BY customer_id ORDER BY item_sales DESC, customer_id LIMIT 20;

-- 7. Product candidates for returns review. Display exposure alongside the rate.
SELECT product_id, COUNT(*) AS sold_items, SUM(returned_item) AS returned_items,
       1.0*SUM(returned_item)/COUNT(*) AS item_return_rate, SUM(item_sales) AS item_sales
FROM analytics_items GROUP BY product_id HAVING COUNT(*)>=50
ORDER BY item_return_rate DESC, sold_items DESC LIMIT 20;

-- 8. Promotion association only. Discount units/meaning are not documented.
SELECT p.promotion_id,p.discount, COUNT(*) AS order_headers,
       SUM(o.item_sales) AS item_sales, SUM(o.has_items) AS sales_backed_orders,
       1.0*SUM(o.item_sales)/NULLIF(SUM(o.has_items),0) AS aov
FROM analytics_orders o JOIN promotions p ON o.promotion_id=p.promotion_id
GROUP BY p.promotion_id,p.discount ORDER BY p.promotion_id;

-- 9. Shipment status labels; there are no dates for measuring delivery duration.
SELECT LOWER(TRIM(status)) AS status, COUNT(*) AS shipments,
       1.0*COUNT(*)/(SELECT COUNT(*) FROM shipments) AS share
FROM shipments GROUP BY LOWER(TRIM(status));

-- 10. Reconciliation and business-rule exceptions.
SELECT SUM(CASE WHEN has_items=0 THEN 1 ELSE 0 END) AS orders_without_items,
       SUM(before_signup) AS orders_before_signup,
       SUM(CASE WHEN ABS(item_sales-payment_amount)>.01 THEN 1 ELSE 0 END) AS payment_mismatches,
       SUM(item_sales)-SUM(payment_amount) AS sales_payment_gap
FROM analytics_orders;
