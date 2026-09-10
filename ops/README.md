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
