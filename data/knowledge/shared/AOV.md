# AOV

## 定义
平均订单金额，总成交额除以总订单数。

## 涉及表
- fact_order：order_amount, order_id

## 示例SQL
```sql
SELECT SUM(order_amount) / COUNT(DISTINCT order_id) AS AOV FROM fact_order
WHERE date_id BETWEEN 20250101 AND 20250331
```

## 标签
[AOV, 客单价, 平均订单金额]

## 元数据
- 创建时间：2026-06-17
- 创建者：admin
- 审核状态：approved
