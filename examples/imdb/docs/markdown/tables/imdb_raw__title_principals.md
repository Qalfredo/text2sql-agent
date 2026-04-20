# Table: imdb_raw.title_principals

## Summary

- Column count: 6
- Primary key columns: None

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| tconst | TEXT | No |  | No |
| ordering | INTEGER | No |  | No |
| nconst | TEXT | Yes |  | No |
| category | TEXT | Yes |  | No |
| job | TEXT | Yes |  | No |
| characters | TEXT | Yes |  | No |

## Foreign Keys

No foreign keys found.

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| idx_title_principals_nconst | nconst | No |
