# IMDb Postgres database schema overview

- Table count: 10

## Tables

| Table | Columns | Foreign Keys | Indexes |
| --- | --- | --- | --- |
| imdb_core.title_genre | 2 | 0 | 1 |
| imdb_core.title_director | 2 | 0 | 1 |
| imdb_core.title_writer | 2 | 0 | 1 |
| imdb_core.name_known_for_title | 2 | 0 | 1 |
| imdb_core.name_primary_profession | 2 | 0 | 1 |
| imdb_raw.title_basics | 9 | 0 | 4 |
| imdb_raw.name_basics | 6 | 0 | 0 |
| imdb_raw.title_ratings | 3 | 0 | 2 |
| imdb_raw.title_principals | 6 | 0 | 1 |
| imdb_raw.title_episode | 4 | 0 | 1 |
