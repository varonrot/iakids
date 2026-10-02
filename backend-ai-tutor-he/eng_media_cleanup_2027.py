"""Drain exact Storage paths queued by an authorized database administrator.

No public endpoint; browsers cannot enqueue jobs. Storage objects are removed
through the API, never by deleting storage.objects metadata with SQL.
"""
from datetime import datetime, timezone

TABLE = '2027_media_cleanup_queue'
ALLOWED_BUCKETS = {'2027-eng-lesson-media', '2027-eng-lesson-audio'}

def drain(sb):
    rows = sb.table(TABLE).select('id,bucket_id,object_path').eq('status', 'pending').limit(500).execute().data or []
    for row in rows:
        if row['bucket_id'] not in ALLOWED_BUCKETS or not row['object_path'] or '..' in row['object_path'].split('/'):
            raise ValueError('Invalid queued media path')
    for bucket in ALLOWED_BUCKETS:
        batch = [r for r in rows if r['bucket_id'] == bucket]
        if not batch:
            continue
        sb.storage.from_(bucket).remove([r['object_path'] for r in batch])
        sb.table(TABLE).update({'status': 'completed', 'completed_at': datetime.now(timezone.utc).isoformat()}).in_('id', [r['id'] for r in batch]).execute()
    print('2027 MEDIA CLEANUP completed:', len(rows))
