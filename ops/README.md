# Server configuration kept in the repo

`smarts-brains.online` is not behind Cloudflare: it is nginx on the application
server, proxying the static site from a container on `127.0.0.1:3020`. That means the
things Cloudflare does for `iakids.app` — compression, caching, the per-IP limit —
have to be configured here, and they were not.

| file | where it lives on the server |
|---|---|
| `nginx-smarts-brains.conf` | `/etc/nginx/sites-enabled/smarts-brains` |

Also changed, in `/etc/nginx/nginx.conf`, the `gzip` block: `gzip_proxied any`,
`gzip_vary on`, `gzip_comp_level 6`, `gzip_min_length 1024` and a `gzip_types` list.
nginx will not compress a **proxied** response without `gzip_proxied`, and with
`gzip_types` commented out it compresses only `text/html` — which is why
`game-sdk.js` was going out at 95,832 bytes.

    game-sdk.js       95,832 B -> 31,340 B
    game-style.css    17,711 B -> 5,004 B
    workspace page   507,043 B -> 102,697 B

The originals are in `/etc/nginx/backups/`. After editing: `nginx -t` then
`systemctl reload nginx` — reload never drops a connection.

Keep this copy in step with the server by hand; nothing deploys it.

## Security headers

Added 2026-09-10, on the mirror only. `iakids.app` is GitHub Pages behind Cloudflare
and cannot set headers itself; the same set has to go on through **Cloudflare →
Rules → Transform Rules → Modify Response Header**, one "Set static" rule per header,
matching `hostname eq "iakids.app"`. The CSP string to paste is the `$iakids_csp`
value in `nginx-smarts-brains.conf`.

Do the mirror first — it is `noindex` and nobody's child depends on it — open a game,
the workspace, the tutor and the parent panel there, and watch the browser console for
`Refused to load…`. Every such line is a source missing from the list. Only once the
mirror is clean is it worth putting the same CSP in front of iakids.app.

`add_header` in a `location` block **replaces** the server-level set rather than
adding to it, which is why the headers are repeated inside the static-asset location.
