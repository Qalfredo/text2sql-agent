# Table: Album

## Summary

- Column count: 3
- Primary key columns: AlbumId

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| AlbumId | INTEGER | No |  | Yes |
| Title | NVARCHAR(160) | No |  | No |
| ArtistId | INTEGER | No |  | No |

## Foreign Keys

| Columns | References | Referenced Columns |
| --- | --- | --- |
| ArtistId | Artist | ArtistId |

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| IFK_AlbumArtistId | ArtistId | No |
