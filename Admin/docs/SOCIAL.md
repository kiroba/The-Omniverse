# KickBack comments and reactions (daemon v8.14.0)

The spec asks for signed "posts, comments, and reactions" and reaction overlays on the feed
(`kickback_complete_architecture_and_feature_spec.md` Module 2, `launch_release_notes.md`). Both are
**person-signed events** (same envelope, verification and rate limit as profiles; see
`PROFILES_AND_CONTACTS.md`): the phone signs, the hub verifies and stores them as signed, peers
re-verify them on sync.

## Post ids

A `post_id` is the id the app already uses for a post card:

- a KickBack post handed to a hub carries the phone-signed envelope, so its id is
  `payload.app_event_id` (`HubFeedEvent.dedupeKey` when the id hashes out);
- a post with no app envelope uses its node `event_id`.

The post does not have to be on this hub yet (it may arrive later via sync). Thread answers say
`post_known: true/false`.

## Write

`POST /api/social/comment` — signed event, `action: "kickback_comment"`, payload:

```json
{"schema": 1, "post_id": "0x<64 hex>", "text": "nice one", "reply_to": "0x<comment event id> (optional)"}
```
`text`: 1-2000 chars, trimmed, newlines allowed.

`POST /api/social/react` — signed event, `action: "kickback_reaction"`, payload (exactly these keys):

```json
{"schema": 1, "post_id": "0x<64 hex>", "reaction": "🔥", "on": true}
```
`reaction`: 1-16 chars, no spaces (an emoji or a short name). `on: false` removes it. For each
(person, post, reaction) the **latest signed `ts` wins**, so reactions toggle and a late-arriving old
event never undoes a newer one; reacting twice counts once.

Answers: 200 `{"status": "SUCCESS", "event_id", ...}` (replay → `"result": "ALREADY_EXISTS"`), 400 schema,
401 signature, 429 rate limit (`OMNI_USER_RATE_MAX` per key per minute, shared with profile updates).
`POST /api/events/append` refuses both actions (403).

## Read

`GET /api/social/thread?post_id=<id>[&limit=1-500][&viewer=<pubkey>]`

```json
{"status": "OK", "post_id": "0x…", "post_known": true,
 "post": {"author_pubkey": "…", "text": "first 280 chars", "ts_ms": 1793334636472},
 "comment_count": 2, "has_more": false,
 "comments": [{"event_id": "0x…", "author_pubkey": "…", "handle_display": "@alice.ab12",
               "text": "first!", "reply_to": null, "ts_ms": 1793334636000, "origin": "remote", "verified": true}],
 "reactions": {"🔥": 2, "lol": 1}, "my_reactions": ["lol"]}
```
Comments are oldest first (by signed ts). `handle_display` is null when the hub has no profile for that
key. `my_reactions` only when `viewer` is given.

`GET /api/social/counts?post_ids=<id>,<id>…[&viewer=<pubkey>]` (max 100 ids) → `{"posts": {"<id>":
{"comments": 3, "reactions": {"🔥": 2}, "my_reactions": [...]}}}` for rendering a feed page in one call.

Every row is re-verified and schema-checked on read; a signed-but-invalid event a peer relayed is
stored (peers only check signatures) but never counted. Reads use SQLite `json_extract` (bundled with
Python's sqlite3 on Windows, Linux and Termux).

## Not built (honest list)

- Editing or deleting a comment: not in the spec; would need a signed tombstone event.
- Follows, DMs, notifications/mentions: not in the spec; not built.
- Moderation, reputation/slashing (spec 1.3), bot detection tiers 1, 2, 4 (attestation, keystroke
  dynamics, entropy analysis): not built. Only tier 3 (per-key rate limit) exists.
- Tipping a post: see `CREDITS_LEDGER.md` (signed transfers with `kind: "tip"` and `ref: <post_id>`, v8.15.0).

## Tests

`tests/test_social.py` (6): validators; thread with comments, replies, handle display, reaction counts
and the viewer's own reactions; toggle with latest-ts-wins and a late old event; batch counts; forged
401, wrong action 400, generic append 403; a signed-but-invalid reaction relayed over `/p2p/sync` is
ignored.
