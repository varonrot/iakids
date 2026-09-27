-- Narration shared by every learner of the same approved English lesson plan.
-- All reads use short-lived signed URLs from the authenticated backend.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('2027-eng-lesson-audio', '2027-eng-lesson-audio', false, 5242880,
        array['audio/wav'])
on conflict (id) do nothing;

-- No anon/authenticated object policies. Only the server service role writes
-- and signs a file after checking parent, child, plan and available step.
