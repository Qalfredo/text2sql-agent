# Table: Employee

## Summary

- Column count: 15
- Primary key columns: EmployeeId

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| EmployeeId | INTEGER | No |  | Yes |
| LastName | NVARCHAR(20) | No |  | No |
| FirstName | NVARCHAR(20) | No |  | No |
| Title | NVARCHAR(30) | Yes |  | No |
| ReportsTo | INTEGER | Yes |  | No |
| BirthDate | DATETIME | Yes |  | No |
| HireDate | DATETIME | Yes |  | No |
| Address | NVARCHAR(70) | Yes |  | No |
| City | NVARCHAR(40) | Yes |  | No |
| State | NVARCHAR(40) | Yes |  | No |
| Country | NVARCHAR(40) | Yes |  | No |
| PostalCode | NVARCHAR(10) | Yes |  | No |
| Phone | NVARCHAR(24) | Yes |  | No |
| Fax | NVARCHAR(24) | Yes |  | No |
| Email | NVARCHAR(60) | Yes |  | No |

## Foreign Keys

| Columns | References | Referenced Columns |
| --- | --- | --- |
| ReportsTo | Employee | EmployeeId |

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| IFK_EmployeeReportsTo | ReportsTo | No |
