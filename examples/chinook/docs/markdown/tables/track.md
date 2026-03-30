# Table: Track

## Summary

- Column count: 9
- Primary key columns: TrackId

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| TrackId | INTEGER | No |  | Yes |
| Name | NVARCHAR(200) | No |  | No |
| AlbumId | INTEGER | Yes |  | No |
| MediaTypeId | INTEGER | No |  | No |
| GenreId | INTEGER | Yes |  | No |
| Composer | NVARCHAR(220) | Yes |  | No |
| Milliseconds | INTEGER | No |  | No |
| Bytes | INTEGER | Yes |  | No |
| UnitPrice | NUMERIC(10,2) | No |  | No |

## Foreign Keys

| Columns | References | Referenced Columns |
| --- | --- | --- |
| MediaTypeId | MediaType | MediaTypeId |
| GenreId | Genre | GenreId |
| AlbumId | Album | AlbumId |

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| IFK_TrackMediaTypeId | MediaTypeId | No |
| IFK_TrackGenreId | GenreId | No |
| IFK_TrackAlbumId | AlbumId | No |
