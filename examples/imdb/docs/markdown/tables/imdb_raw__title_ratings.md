# Table: imdb_raw.title_ratings

## Summary

- Column count: 3
- Primary key columns: None

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| tconst | TEXT | No |  | No |
| average_rating | NUMERIC(3, 1) | Yes |  | No |
| num_votes | INTEGER | Yes |  | No |

## Foreign Keys

No foreign keys found.

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| idx_title_ratings_average_rating | average_rating | No |
| idx_title_ratings_num_votes | num_votes | No |
