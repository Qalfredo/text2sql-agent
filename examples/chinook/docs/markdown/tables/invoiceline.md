# Table: InvoiceLine

## Summary

- Column count: 5
- Primary key columns: InvoiceLineId

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| InvoiceLineId | INTEGER | No |  | Yes |
| InvoiceId | INTEGER | No |  | No |
| TrackId | INTEGER | No |  | No |
| UnitPrice | NUMERIC(10,2) | No |  | No |
| Quantity | INTEGER | No |  | No |

## Foreign Keys

| Columns | References | Referenced Columns |
| --- | --- | --- |
| TrackId | Track | TrackId |
| InvoiceId | Invoice | InvoiceId |

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| IFK_InvoiceLineTrackId | TrackId | No |
| IFK_InvoiceLineInvoiceId | InvoiceId | No |
