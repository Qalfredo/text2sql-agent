# Table: imdb_raw.title_basics

## Summary

- Column count: 9
- Primary key columns: None

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| tconst | TEXT | No |  | No |
| title_type | TEXT | Yes |  | No |
| primary_title | TEXT | Yes |  | No |
| original_title | TEXT | Yes |  | No |
| is_adult | BOOLEAN | Yes |  | No |
| start_year | INTEGER | Yes |  | No |
| end_year | INTEGER | Yes |  | No |
| runtime_minutes | INTEGER | Yes |  | No |
| genres | TEXT | Yes |  | No |

## Foreign Keys

No foreign keys found.

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| idx_title_basics_original_title | original_title | No |
| idx_title_basics_primary_title | primary_title | No |
| idx_title_basics_start_year | start_year | No |
| idx_title_basics_title_type | title_type | No |
