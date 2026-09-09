# Backlog

Known work that is deliberately deferred, not forgotten. Each entry says what
the problem is, why it matters, and where to start.

---

## Matching ignores when a photo was taken

`taken_at` is recorded on every sighting (EXIF `DateTimeOriginal`, converted
from the photo's local time to UTC on the client), but nothing reads it.

`run_matching` filters candidates on `LostStatus.ACTIVE` and geography only —
see `find_candidate_declarations` in `src/services/matching_service.py:75-108`.
The combined score is 70% image similarity and 30% distance decay
(`exp(-dist/3km)`); time is not a term. So a photo taken six months ago scores
exactly like one taken ten minutes ago, and can raise a match — with a push
notification — for a pet that went missing long after the photo was shot.

Two directions, not mutually exclusive:

- **Exclude** sightings whose `taken_at` predates `LostDeclaration.created_at`
  (or `last_seen`). The pet demonstrably was not lost yet, so the photo cannot
  be of the lost animal. This is the sharper, safer rule.
- **Damp** the score by age, in the shape of the existing distance decay, so a
  stale sighting ranks below a fresh one rather than vanishing.

`taken_at` is nullable — camera captures and stripped photos have none — so
whatever rule is chosen must treat "unknown age" as neutral, not as stale, or
every camera sighting silently loses rank.

Worth checking against real data before tuning: the sightings table already has
`taken_at` populated on rows whose `location_source` is `DEVICE`, because
`DateTimeOriginal` survives even where Android redacts GPS.

---

## A clean install loses the configured server address

`ServerConfig` persists the backend host in `FlutterSecureStorage`
(`mobile/lib/core/config/server_config.dart`), which an uninstall wipes. The
build-time default is `https://pets.example.com` — a placeholder that does not
resolve — so a fresh install fails with a bare DNS error:

```
DioException [connection error]: Failed host lookup: 'pets.example.com'
SocketException: No address associated with hostname, errno = 7
```

Nothing points the user at Settings, and the failure reads like a backend
outage rather than a missing configuration. It surfaced during EXIF testing
after a deliberate uninstall, and cost a debugging detour.

Options:

- Default `API_HOST` to empty and treat "no host configured" as a distinct
  state: send the user to Settings with "No server configured" instead of
  attempting a request that cannot succeed.
- Detect the placeholder host specifically and show the same guidance.
- Keep passing `--dart-define=API_HOST=...` at build time, which is the current
  workaround and fine for development but does not help a real first run.

The empty-default option is the honest one: it makes an unconfigured build fail
in a way that names its own cause.
