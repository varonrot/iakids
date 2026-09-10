-- IAKIDS: which country a family is in.
--
-- Nothing in the database says where anyone is: Google hands back a name, an email
-- and a picture, and that is all we ever stored. So "how many customers, and from
-- where" has no answer today, and the one paying customer who is not the owner can
-- only be guessed at from the spelling of a name.
--
-- Cloudflare already knows. Every request through it carries the country, and it
-- publishes the answer to the page itself at /cdn-cgi/trace — so the browser can read
-- its own country without a server, an IP lookup service, or a third party.
--
-- What is stored is the country, the region and the browser's own timezone. **Not the
-- IP address.** An IP is personal data, it identifies a household rather than a
-- country, and it would sit in a database about children; the country is what the
-- question actually needs. The timezone comes from the browser and covers the mirror
-- domain, which does not go through Cloudflare and so has no /cdn-cgi/trace.
--
-- One row per user, overwritten as they travel; first_seen keeps the original.
-- Idempotent: safe to paste more than once.

create table if not exists public.user_locations (
    user_id     uuid primary key references auth.users (id) on delete cascade,
    country     text,                       -- ISO-3166 alpha-2, from Cloudflare
    region      text,
    timezone    text,                       -- IANA, from the browser
    source      text,                       -- 'cloudflare' | 'timezone'
    first_seen  timestamptz not null default now(),
    last_seen   timestamptz not null default now(),
    first_country text                      -- where they were the first time we asked
);

alter table public.user_locations enable row level security;

-- A parent may see their own row and nothing else. Writing goes through the function
-- below, which is the only thing that may set a country, so a client cannot claim to
-- be somewhere it is not by writing the row directly.
drop policy if exists user_locations_read_own on public.user_locations;
create policy user_locations_read_own on public.user_locations
    for select using (user_id = auth.uid());

create or replace function public.record_user_location(
    p_country text default null, p_region text default null,
    p_timezone text default null, p_source text default null)
returns void
language plpgsql security definer set search_path = public as $$
declare
    c text := nullif(upper(substring(coalesce(p_country, '') from 1 for 2)), '');
    r text := nullif(substring(coalesce(p_region, '') from 1 for 80), '');
    z text := nullif(substring(coalesce(p_timezone, '') from 1 for 64), '');
begin
    if auth.uid() is null then
        raise exception 'not signed in' using errcode = '42501';
    end if;
    -- Cloudflare answers XX for an address it cannot place, and T1 for Tor.
    if c is not null and c !~ '^[A-Z]{2}$' then c := null; end if;

    insert into public.user_locations (user_id, country, region, timezone, source, first_country)
    values (auth.uid(), c, r, z, nullif(p_source, ''), c)
    on conflict (user_id) do update
       set country   = coalesce(excluded.country, user_locations.country),
           region    = coalesce(excluded.region, user_locations.region),
           timezone  = coalesce(excluded.timezone, user_locations.timezone),
           source    = coalesce(excluded.source, user_locations.source),
           last_seen = now(),
           first_country = coalesce(user_locations.first_country, excluded.country);
end;
$$;

revoke all on function public.record_user_location(text, text, text, text) from public, anon;
grant execute on function public.record_user_location(text, text, text, text) to authenticated;

comment on table public.user_locations is
    'Country and timezone per parent account, from Cloudflare''s /cdn-cgi/trace and the browser. No IP address is stored: the country is what the question needs and an IP identifies a household.';
