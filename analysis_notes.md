# Retail Sales & Customer Analytics
## Analysis Notes

This document records the exploratory data analysis performed on the
Retail Sales & Customer Analytics dataset. The purpose of this phase is
to understand the structure, coverage, quality, and basic characteristics
of the data before performing data cleaning and business analysis.

---

## 1. Dataset Size

| Table | Rows |
|---|---:|
| Categories | 30 |
| Customers | 50,000 |
| Employees | 1,000 |
| Order Items | 600,000 |
| Orders | 300,000 |
| Payments | 300,000 |
| Products | 10,000 |
| Promotions | 50 |
| Returns | 30,000 |
| Shipments | 300,000 |
| Stores | 100 |
| Suppliers | 200 |

### Observation

The dataset contains a substantial volume of retail transactional data,
including 300,000 orders and 600,000 individual order items.

The data covers multiple areas of the retail operation, including customers,
products, stores, employees, suppliers, promotions, payments, shipments,
and product returns. This provides sufficient relational data for analyzing
sales performance, customer purchasing behavior, product performance,
store performance, promotions, and returns.

---

## 2. Analysis Period

**First Order:** 2020-01-01  
**Last Order:** 2024-01-01

### Observation

The order data ranges from January 1, 2020 to January 1, 2024. Therefore,
the dataset contains transaction records spanning approximately four years.

This period provides enough historical data to investigate sales trends
and changes in retail performance over time.

---

## 3. Customer Signup Period

**Earliest Signup:** 2019-01-01  
**Latest Signup:** 2024-01-01

### Observation

Customer signup records range from January 1, 2019 to January 1, 2024.

The signup data begins before the first recorded order date, indicating that
some customers were registered before the transaction period represented
in the orders table.

The signup dates may later be used to analyze customer acquisition and
customer tenure.

---

## 4. Missing Values

### Customers

| Column | Missing |
|---|---:|
| customer_id | 0 |
| city | 0 |
| signup_date | 0 |

### Orders

| Column | Missing |
|---|---:|
| order_id | 0 |
| customer_id | 0 |
| store_id | 0 |
| order_date | 0 |
| promotion_id | 0 |

### Order Items

| Column | Missing |
|---|---:|
| order_item_id | 0 |
| order_id | 0 |
| product_id | 0 |
| qty | 0 |
| price | 0 |

### Observation

No missing values were identified in the examined customer, order, and
order item columns.

Important identifiers such as customer IDs, order IDs, product IDs, and
store IDs are complete. Transaction-related fields such as order dates,
quantities, and prices are also complete.

The `promotion_id` field also contains no missing values, indicating that
every order in this dataset is associated with a promotion record. This is
worth investigating further when promotion performance is analyzed.

---

## 5. Quantity Quality

**Minimum Quantity:** 1  
**Maximum Quantity:** 4  
**Average Quantity:** 2.50  
**Zero/Negative Quantities:** 0

### Observation

Order quantities range from 1 to 4 units, with an average quantity of
approximately 2.50 units per order item.

No zero or negative quantities were identified. Therefore, no immediately
invalid quantity values were detected during the initial data quality check.

---

## 6. Transaction Price Quality

**Minimum Price:** 100  
**Maximum Price:** 4,999  
**Average Price:** 2,550.25  
**Zero/Negative Prices:** 0

### Observation

Transaction prices range from 100 to 4,999, with an average transaction
price of approximately 2,550.25.

No zero or negative transaction prices were identified. Therefore, all
order item prices fall within a positive numerical range.

However, transaction prices still need to be compared with product prices
to understand how pricing is represented within the dataset.

---

## 7. Product vs Transaction Price

The `products.price` column contains a price associated with each product,
while `order_items.price` contains the price recorded for an individual
order item.

The following sample shows transactions where the transaction price differs
from the corresponding product price.

| Product ID | Product Price | Transaction Price |
|---:|---:|---:|
| 1 | 3,987 | 4,501 |
| 1 | 3,987 | 1,087 |
| 1 | 3,987 | 2,486 |
| 1 | 3,987 | 2,144 |
| 1 | 3,987 | 3,757 |
| 1 | 3,987 | 379 |
| 1 | 3,987 | 4,441 |
| 1 | 3,987 | 1,354 |
| 1 | 3,987 | 4,244 |
| 1 | 3,987 | 4,171 |
| 1 | 3,987 | 2,349 |
| 1 | 3,987 | 4,915 |
| 1 | 3,987 | 2,494 |
| 1 | 3,987 | 2,167 |
| 1 | 3,987 | 2,369 |
| 1 | 3,987 | 3,954 |
| 1 | 3,987 | 2,891 |
| 1 | 3,987 | 4,692 |
| 1 | 3,987 | 4,830 |
| 1 | 3,987 | 695 |

### Observation

Product ID 1 has a product price of 3,987, while its transaction prices
vary considerably across individual order items. In this sample,
transaction prices range from 379 to 4,915.

This demonstrates that `products.price` and `order_items.price` cannot
automatically be treated as equivalent measures.

The cause of these differences has not yet been established. Possible
explanations could include promotional pricing, historical pricing,
transaction-specific pricing, or characteristics of the synthetic dataset.
Further analysis is required before assigning a specific explanation.

For preliminary sales calculations, `order_items.price` will be used as
the transaction-level price because it is recorded directly on each
individual order item. This assumption will be reviewed as the relationship
between products, promotions, payments, and orders is investigated further.

---

## 8. Shipment Status Distribution

| Status | Shipments |
|---|---:|
| Shipped | 100,283 |
| Delivered | 99,862 |
| Late | 99,855 |
| **Total** | **300,000** |

### Observation

The shipment table contains three distinct shipment statuses: `shipped`,
`delivered`, and `late`.

The distribution is relatively balanced, with approximately one-third of
the 300,000 shipment records belonging to each status.

No `cancelled` shipment status was identified. Therefore, shipment status
alone does not currently provide evidence of cancelled orders that would
need to be excluded from sales calculations.

The meaning of `shipped`, `delivered`, and `late` should still be considered
when shipment performance is analyzed later in the project.

---

## 9. Returns

**Total Returns:** 30,000  
**Minimum Refund:** 50  
**Maximum Refund:** 4,999  
**Average Refund:** 2,532.08  
**Total Refunds:** 75,962,300  
**Negative Refunds:** 0

### Observation

The dataset contains 30,000 return records with total recorded refunds of
75,962,300.

Refund amounts range from 50 to 4,999, with an average refund of
approximately 2,532.08.

No negative refund values were identified.

Because returns represent refunded transactions, the total refund amount
may need to be considered when calculating net revenue. The relationship
between returns and the original order items should be investigated before
the final revenue calculation is defined.

---

## 10. Payments

**Total Payments:** 300,000  
**Minimum Payment:** 100  
**Maximum Payment:** 19,999  
**Average Payment:** 10,060.27  
**Total Payment Amount:** 3,018,080,810  
**Zero/Negative Payments:** 0

### Observation

The payments table contains 300,000 payment records, which is equal to the
number of orders in the dataset.

Payment amounts range from 100 to 19,999, with an average payment amount
of approximately 10,060.27.

No zero or negative payment amounts were identified.

The total recorded payment amount is 3,018,080,810. This differs from the
preliminary gross revenue calculated from order items, which indicates that
payment amounts and calculated order-item revenue should be compared at the
individual order level before determining the appropriate revenue measure.

---

## 11. Relationship Validation

**Orders without Customers:** 0  
**Order Items without Orders:** 0  
**Order Items without Products:** 0

### Observation

No orphaned records were identified in the tested relationships.

Every order references an existing customer, every order item references
an existing order, and every order item references an existing product.

This indicates that the core customer, order, order item, and product
relationships are structurally consistent based on the relationship checks
performed during exploration.

---

## 12. Preliminary Gross Revenue

**Gross Revenue:** 3,827,746,136

### Calculation

`Gross Revenue = SUM(Quantity × Transaction Price)`

### Observation

Using quantity multiplied by the transaction-level price recorded in
`order_items`, the dataset produces preliminary gross revenue of
3,827,746,136.

This value should not yet be considered final business revenue.

The dataset also contains 75,962,300 in recorded refunds, while the payments
table contains total payments of 3,018,080,810. These differences indicate
that the relationship between calculated order totals, recorded payments,
returns, and promotions requires further investigation.

A final definition of gross and net revenue will therefore be established
during the business-rule and data-preparation phase.

---

## 13. Preliminary KPIs

| KPI | Value |
|---|---:|
| Total Orders | 300,000 |
| Purchasing Customers | 49,886 |
| Units Sold | 1,500,518 |
| Preliminary Gross Revenue | 3,827,746,136 |

### Observation

The dataset contains 300,000 orders placed by 49,886 distinct purchasing
customers.

A total of 1,500,518 units were sold across the 600,000 order-item records.

The customer table contains 50,000 registered customers, while 49,886
customers appear in the orders table. This means that 114 registered
customers do not appear as purchasing customers during the analyzed
transaction period.

These preliminary KPIs provide a high-level view of the dataset but will
be refined after the remaining business rules have been investigated.

---

# Data Exploration Summary

## Dataset

- **Analysis Period:** 2020-01-01 to 2024-01-01
- **Total Orders:** 300,000
- **Registered Customers:** 50,000
- **Purchasing Customers:** 49,886
- **Total Order Items:** 600,000
- **Total Products:** 10,000
- **Total Units Sold:** 1,500,518
- **Stores:** 100
- **Suppliers:** 200
- **Promotions:** 50

## Data Quality

- **Missing Values:** No missing values identified in the examined customer,
  order, and order-item fields.
- **Invalid Quantities:** 0
- **Invalid Prices:** 0
- **Invalid Payments:** 0
- **Invalid Refunds:** 0
- **Orders without Customers:** 0
- **Order Items without Orders:** 0
- **Order Items without Products:** 0

Overall, the initial exploration found no obvious missing, non-positive, or
orphaned values in the core fields examined.

## Business Data

- **Shipment Statuses:** Shipped, Delivered, Late
- **Total Shipments:** 300,000
- **Total Returns:** 30,000
- **Total Refunds:** 75,962,300
- **Total Recorded Payments:** 3,018,080,810
- **Preliminary Gross Revenue:** 3,827,746,136

## Key Findings from Exploration

1. The dataset contains 300,000 orders and 600,000 order items covering
   approximately four years of retail transactions.

2. The core fields examined contain no missing values, invalid quantities,
   invalid prices, invalid payments, negative refunds, or orphaned records.

3. Product prices and transaction-level prices can differ substantially.
   The reason for these differences has not yet been established and
   requires further investigation.

4. The shipment data contains three statuses: `shipped`, `delivered`, and
   `late`. No cancelled shipment status was observed.

5. The customer table contains 50,000 registered customers, while 49,886
   distinct customers placed at least one order during the analyzed period.
   Therefore, 114 registered customers do not appear in the order data.

6. Preliminary gross revenue calculated from order items is 3,827,746,136,
   while recorded payments total 3,018,080,810. This difference requires
   investigation before selecting the final revenue metric.

7. The dataset contains 30,000 returns totaling 75,962,300 in refunds.
   Returns will need to be incorporated appropriately when defining net
   revenue.

## Issues Requiring Further Investigation

1. **Product Price vs Transaction Price**

   Determine why `order_items.price` frequently differs from
   `products.price` and whether promotions or another dataset rule explains
   the difference.

2. **Calculated Order Revenue vs Payments**

   Compare each order's calculated value from `order_items` against the
   corresponding `payments.amount` to understand why total calculated gross
   revenue differs from total recorded payments.

3. **Returns and Revenue**

   Determine how refunds relate to individual order items and establish
   whether and how refunds should be deducted when calculating net revenue.

4. **Promotion Behavior**

   Every examined order contains a `promotion_id`. The relationship between
   promotions, transaction prices, and payment amounts should be analyzed
   to determine how promotions are represented in the dataset.

## Next Steps

The next phase will focus on investigating the issues identified during
data exploration before making any modifications to the dataset.

The main objectives are to:

1. Analyze the relationship between product prices and transaction prices.
2. Compare calculated order totals with recorded payment amounts.
3. Investigate how promotions affect transactions.
4. Validate how returns and refunds should affect revenue.
5. Establish clear definitions for gross revenue and net revenue.
6. Determine whether any actual data cleaning or transformation is required.

After these business rules have been established, the dataset can be
prepared for detailed sales analysis, customer analysis, and Power BI
visualization.