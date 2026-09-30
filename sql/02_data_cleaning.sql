-- Preparation views. Run after loading the 12 CSVs into the selected database.
-- Compatible with MySQL 8+ and SQLite. No raw records are updated or deleted.
-- See docs/methodology.md for unresolved business rules and metric definitions.
-- Rebuild only these project-owned views when refreshing.
DROP VIEW IF EXISTS analytics_orders;
DROP VIEW IF EXISTS analytics_items;
DROP VIEW IF EXISTS analytics_refunds;

CREATE VIEW analytics_refunds AS
SELECT order_item_id, COUNT(*) AS return_records, SUM(refund) AS refund_amount
FROM returns GROUP BY order_item_id;

CREATE VIEW analytics_items AS
SELECT oi.order_item_id, oi.order_id, oi.product_id, oi.qty, oi.price,
       oi.qty * oi.price AS item_sales,
       COALESCE(r.return_records, 0) AS return_records,
       COALESCE(r.refund_amount, 0) AS refund_amount,
       CASE WHEN r.return_records > 0 THEN 1 ELSE 0 END AS returned_item,
       CASE WHEN r.refund_amount > oi.qty * oi.price THEN 1 ELSE 0 END AS refund_exceeds_sales
FROM order_items oi
LEFT JOIN analytics_refunds r ON oi.order_item_id = r.order_item_id;

CREATE VIEW analytics_orders AS
SELECT o.order_id, o.customer_id, o.store_id, o.order_date, o.promotion_id,
       COALESCE(i.item_sales, 0) AS item_sales,
       COALESCE(i.units, 0) AS units,
       COALESCE(i.item_count, 0) AS item_count,
       COALESCE(i.refund_amount, 0) AS refund_amount,
       CASE WHEN i.item_count > 0 THEN 1 ELSE 0 END AS has_items,
       CASE WHEN i.returned_items > 0 THEN 1 ELSE 0 END AS has_return,
       p.payment_amount, p.payment_records,
       CASE WHEN o.order_date < c.signup_date THEN 1 ELSE 0 END AS before_signup
FROM orders o
LEFT JOIN (
    SELECT order_id, SUM(item_sales) AS item_sales, SUM(qty) AS units,
           COUNT(*) AS item_count, SUM(refund_amount) AS refund_amount,
           SUM(returned_item) AS returned_items
    FROM analytics_items GROUP BY order_id
) i ON o.order_id = i.order_id
LEFT JOIN (
    SELECT order_id, SUM(amount) AS payment_amount, COUNT(*) AS payment_records
    FROM payments GROUP BY order_id
) p ON o.order_id = p.order_id
LEFT JOIN customers c ON o.customer_id = c.customer_id;
