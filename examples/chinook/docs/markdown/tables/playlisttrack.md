# Table: PlaylistTrack

## Summary

- Column count: 2
- Primary key columns: PlaylistId, TrackId

## Columns

| Column | Type | Nullable | Default | Primary Key |
| --- | --- | --- | --- | --- |
| PlaylistId | INTEGER | No |  | Yes |
| TrackId | INTEGER | No |  | Yes |

## Foreign Keys

| Columns | References | Referenced Columns |
| --- | --- | --- |
| TrackId | Track | TrackId |
| PlaylistId | Playlist | PlaylistId |

## Indexes

| Index | Columns | Unique |
| --- | --- | --- |
| IFK_PlaylistTrackTrackId | TrackId | No |
| IFK_PlaylistTrackPlaylistId | PlaylistId | No |
| sqlite_autoindex_PlaylistTrack_1 | PlaylistId, TrackId | Yes |
