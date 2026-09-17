-- ROLLBACK of 20260917_restore_app_admins_grant.sql  ·  2026-09-17
--
-- Closes app_admins to the browser again. Only run this once the support_tickets
-- policy no longer reads the table directly (a SECURITY DEFINER is_app_admin() helper),
-- otherwise reading support tickets breaks again with
--     permission denied for table app_admins
--
-- Idempotent: safe to run more than once.

revoke all on public.app_admins from anon, authenticated;

notify pgrst, 'reload schema';
