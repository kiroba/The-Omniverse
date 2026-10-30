# Request bodies: Content-Length or chunked (daemon v8.12.1)

## The bug this fixes (KickBack "No posts yet" with events in the log)

KickBack hands each signed post to the hub with `OmniHubClient._post`
(`packages/omni_core_ui/lib/src/omni_hub_client.dart`). It wrote the JSON with `req.write(...)` and
never set `contentLength`, so `dart:io` sent the body as `Transfer-Encoding: chunked` with **no
`Content-Length` header**.

Every daemon up to v8.12.0 read `/api/events/append` bodies only by `Content-Length`. Missing header ->
length 0 -> body `"{}"` -> the event was stored with the default action `USER_ACTION`, an empty payload
and a fresh `ts`, and the daemon answered `{"status": "SUCCESS"}`. The app then marked the post as
synced. KickBack's shared feed asks for `GET /api/events/feed?type=KICKBACK_POST`, which never matched
those empty rows. So:

- a fresh daemon has 1 event (genesis); each phone post adds one empty `USER_ACTION` row
  ("2 events in its log" after one post);
- no post ever reached another phone or the feed, on any daemon version, local or remote hub;
- the post still shows on the phone that wrote it (from its own SQLite log), unless that app's data
  was cleared (reinstall), in which case the feed is empty.

Reproduced in the sandbox with daemon v8.8.1 and the app's own Dart code (LocalEventStore +
OmniHubClient + HubFeedCache + mergeFeed run under Dart 3.13.7 with sqflite_common_ffi).

Bug reports and the OmniCast signal client already set `contentLength` (the hub answers 411 without
it), so they were not affected.

## What changed

- `read_request_body(handler, max_bytes)`: reads a `Content-Length` body **or** a
  `Transfer-Encoding: chunked` body (chunk extensions and trailers are accepted and ignored).
  413 past the endpoint's cap, 400 for malformed framing.
- `POST /api/events/append`: uses it (cap 5 MB as before). An empty body, `{}`, or a non-object
  answers **400** and stores nothing. Counted as `append_rejected_body` in telemetry.
- `POST /api/bugs/report`, `/api/signal/send`, `/api/credits/*`: chunked bodies are accepted too.
  No body at all still answers 411.
- The app side is fixed separately (main branch PR): `_post` now sends `Content-Length`, and a
  one-time local migration re-sends posts that were marked synced while the daemon stored them empty.

## Cleaning up old empty rows

The empty `USER_ACTION` rows already in a daemon's `continuity_events.db` are signed chain events;
they are harmless and are left alone (deleting them would break the hash chain). They show up in
`/api/events/feed` without a type filter and in `events_by_action` in the telemetry summary.

## Tests

`tests/test_request_bodies.py`: unit tests of the reader (length, none, chunked with extension +
trailer, too large, malformed) and a live daemon receiving a chunked KickBack post exactly as Dart sends
it (it lands in `?type=KICKBACK_POST` with its text and app envelope), a post split over three chunks,
empty/`{}`/non-object appends refused and not stored, malformed chunk 400, chunked bug report and
signal bodies parsed, chunked oversize 413.
