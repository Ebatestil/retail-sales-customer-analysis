-- RETAIL SALES & CUSTOMER ANALYTICS
-- DATA EXPLORATION

USE retail_analytics;

-- 1. DATASET SIZE
-- Purpose: Verify the number of records in each table.

SELECT 'categories' AS table_name, COUNT(*) AS row_count FROM categories
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'employees', COUNT(*) FROM employees
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'payments', COUNT(*) FROM payments
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'promotions', COUNT(*) FROM promotions
UNION ALL
SELECT 'returns', COUNT(*) FROM returns
UNION ALL
SELECT 'shipments', COUNT(*) FROM shipments
UNION ALL
SELECT 'stores', COUNT(*) FROM stores
UNION ALL
SELECT 'suppliers', COUNT(*) FROM suppliers;

-- 2. ANALYSIS PERIOD
-- Purpose: Determine the date range covered by the dataset.

SELECT
    MIN(order_date) AS first_order_date,
    MAX(order_date) AS last_order_date
FROM orders;

-- 3. CUSTOMER SIGNUP PERIOD

SELECT
    MIN(signup_date) AS earliest_signup,
    MAX(signup_date) AS latest_signup
FROM customers;

-- 4. MISSING VALUES

-- CUSTOMERS
SELECT
    SUM(customer_id IS NULL) AS missing_customer_id,
    SUM(city IS NULL) AS missing_city,
    SUM(signup_date IS NULL) AS missing_signup_date
FROM customers;

-- ORDERS

SELECT
    SUM(order_id IS NULL) AS missing_order_id,
    SUM(customer_id IS NULL) AS missing_customer_id,
    SUM(store_id IS NULL) AS missing_store_id,
    SUM(order_date IS NULL) AS missing_order_date,
    SUM(promotion_id IS NULL) AS missing_promotion_id
FROM orders;

-- ORDER ITEMS

SELECT
    SUM(order_item_id IS NULL) AS missing_order_item_id,
    SUM(order_id IS NULL) AS missing_order_id,
    SUM(product_id IS NULL) AS missing_product_id,
    SUM(qty IS NULL) AS missing_qty,
    SUM(price IS NULL) AS missing_price
FROM order_items;

-- 5. QUANTITY QUALITY

SELECT
    MIN(qty) AS minimum_quantity,
    MAX(qty) AS maximum_quantity,
    ROUND(AVG(qty), 2) AS average_quantity
FROM order_items;

SELECT
    COUNT(*) AS invalid_quantities
FROM order_items
WHERE qty <= 0;

-- 6. TRANSACTION PRICE QUALITY

SELECT
    MIN(price) AS minimum_price,
    MAX(price) AS maximum_price,
    ROUND(AVG(price), 2) AS average_price
FROM order_items;

SELECT
    COUNT(*) AS invalid_prices
FROM order_items
WHERE price <= 0;

-- 7. PRODUCT PRICE VS TRANSACTION PRICE

SELECT
    COUNT(*) AS different_prices
FROM order_items oi
JOIN products p
    ON oi.product_id = p.product_id
WHERE oi.price <> p.price;

--Inspect examples

SELECT
    oi.product_id,
    p.price AS product_price,
    oi.price AS transaction_price
FROM order_items oi
JOIN products p
    ON oi.product_id = p.product_id
WHERE oi.price <> p.price
LIMIT 20;

-- 8. SHIPMENT STATUS

SELECT
    status,
    COUNT(*) AS total_shipments
FROM shipments
GROUP BY status
ORDER BY total_shipments DESC;

-- 9. RETURN ANALYSIS

SELECT
    COUNT(*) AS total_returns,
    MIN(refund) AS minimum_refund,
    MAX(refund) AS maximum_refund,
    ROUND(AVG(refund), 2) AS average_refund,
    SUM(refund) AS total_refunds
FROM returns;

SELECT
    COUNT(*) AS invalid_refunds
FROM returns
WHERE refund < 0;

-- 10. PAYMENTS

SELECT
    COUNT(*) AS total_payments,
    MIN(amount) AS minimum_payment,
    MAX(amount) AS maximum_payment,
    ROUND(AVG(amount), 2) AS average_payment,
    SUM(amount) AS total_payment_amount
FROM payments;

SELECT
    COUNT(*) AS invalid_payments
FROM payments
WHERE amount <= 0;

-- 11. REFERENTIAL INTEGRITY

SELECT COUNT(*) AS orders_without_customer
FROM orders o
LEFT JOIN customers c
    ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

SELECT COUNT(*) AS items_without_order
FROM order_items oi
LEFT JOIN orders o
    ON oi.order_id = o.order_id
WHERE o.order_id IS NULL;

SELECT COUNT(*) AS items_without_product
FROM order_items oi
LEFT JOIN products p
    ON oi.product_id = p.product_id
WHERE p.product_id IS NULL;

-- 12. PRELIMINARY GROSS REVENUE

SELECT
    SUM(qty * price) AS gross_revenue
FROM order_items;

-- 13. BASIC KPIs

SELECT
    COUNT(DISTINCT order_id) AS total_orders
FROM orders;

