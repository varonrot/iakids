-- Remove this bucket only after separately deleting its cached lesson audio.
delete from storage.buckets
where id = '2027-eng-lesson-audio'
  and not exists (select 1 from storage.objects where bucket_id = '2027-eng-lesson-audio');
