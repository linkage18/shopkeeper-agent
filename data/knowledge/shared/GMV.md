# GMV

## 定义
成交总额，所有订单金额的加总。

## 涉及表
- fact_order：order_amount

## 示例SQL
```sql
SELECT SUM(order_amount) AS GMV FROM fact_order
WHERE date_id BETWEEN 20250101 AND 20250331
```

## 标签
[GMV, 成交总额, 销售额]

## 元数据
- 创建时间：2026-06-17
- 创建者：admin
- 审核状态：approved
