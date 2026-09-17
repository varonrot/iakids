-- IAKIDS: put back the grant on app_admins.  2026-09-17
--
-- Run this if 20260917_revoke_browser_table_access.sql was applied with app_admins in
-- the list. Revoking it broke reading support_tickets: a row level policy there asks
-- "is this user in app_admins", policies run with the caller's own rights, and the
-- moment the caller cannot read app_admins the policy itself fails with
--     permission denied for table app_admins
-- A signed-in user opening /support then sees an error instead of their tickets.
--
-- app_admins is empty and holds only admin user ids, so this grant gives nothing away
-- that matters. The real fix is a SECURITY DEFINER is_app_admin() helper and a policy
-- that calls it, so the table can close without the policy noticing.
--
-- Idempotent: safe to run more than once.

grant select on public.app_admins to authenticated;

notify pgrst, 'reload schema';
