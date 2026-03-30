# Table: Customer

## Summary

- Column count: 13
- Primary key columns: CustomerId

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| CustomerId | INTEGER | No |  | Yes |
| FirstName | NVARCHAR(40) | No |  | No |
| LastName | NVARCHAR(20) | No |  | No |
| Company | NVARCHAR(80) | Yes |  | No |
| Address | NVARCHAR(70) | Yes |  | No |
| City | NVARCHAR(40) | Yes |  | No |
| State | NVARCHAR(40) | Yes |  | No |
| Country | NVARCHAR(40) | Yes |  | No |
| PostalCode | NVARCHAR(10) | Yes |  | No |
| Phone | NVARCHAR(24) | Yes |  | No |
| Fax | NVARCHAR(24) | Yes |  | No |
| Email | NVARCHAR(60) | No |  | No |
| SupportRepId | INTEGER | Yes |  | No |

## Foreign Keys

| Columns | References | Referenced Columns |
| --- | --- | --- |
| SupportRepId | Employee | EmployeeId |

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| IFK_CustomerSupportRepId | SupportRepId | No |
