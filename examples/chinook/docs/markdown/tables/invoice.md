# Table: Invoice

## Summary

- Column count: 9
- Primary key columns: InvoiceId

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| InvoiceId | INTEGER | No |  | Yes |
| CustomerId | INTEGER | No |  | No |
| InvoiceDate | DATETIME | No |  | No |
| BillingAddress | NVARCHAR(70) | Yes |  | No |
| BillingCity | NVARCHAR(40) | Yes |  | No |
| BillingState | NVARCHAR(40) | Yes |  | No |
| BillingCountry | NVARCHAR(40) | Yes |  | No |
| BillingPostalCode | NVARCHAR(10) | Yes |  | No |
| Total | NUMERIC(10,2) | No |  | No |

## Foreign Keys

| Columns | References | Referenced Columns |
| --- | --- | --- |
| CustomerId | Customer | CustomerId |

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| IFK_InvoiceCustomerId | CustomerId | No |
