# Table: imdb_raw.title_episode

## Summary

- Column count: 4
- Primary key columns: None

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| tconst | TEXT | No |  | No |
| parent_tconst | TEXT | Yes |  | No |
| season_number | INTEGER | Yes |  | No |
| episode_number | INTEGER | Yes |  | No |

## Foreign Keys

No foreign keys found.

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| idx_title_episode_parent | parent_tconst, season_number, episode_number | No |
