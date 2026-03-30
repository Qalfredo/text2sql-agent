# Chinook SQLite database schema overview

- Table count: 11

## Tables

| Table | Columns | Foreign Keys | Indexes |
| --- | --- | --- | --- |
| Album | 3 | 1 | 1 |
| Artist | 2 | 0 | 0 |
| Customer | 13 | 1 | 1 |
| Employee | 15 | 1 | 1 |
| Genre | 2 | 0 | 0 |
| Invoice | 9 | 1 | 1 |
| InvoiceLine | 5 | 2 | 2 |
| MediaType | 2 | 0 | 0 |
| Playlist | 2 | 0 | 0 |
| PlaylistTrack | 2 | 2 | 3 |
| Track | 9 | 3 | 3 |
