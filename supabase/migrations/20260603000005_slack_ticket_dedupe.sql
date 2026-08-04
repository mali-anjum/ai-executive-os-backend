-- Alembic revision 005: dedupe Slack tickets + partial unique index.

DELETE FROM public.tickets t
USING (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY org_id, slack_channel_id, slack_message_ts
               ORDER BY created_at ASC, id ASC
           ) AS rn
    FROM public.tickets
    WHERE slack_channel_id IS NOT NULL
      AND slack_message_ts IS NOT NULL
) d
WHERE t.id = d.id AND d.rn > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tickets_slack_message
    ON public.tickets (org_id, slack_channel_id, slack_message_ts)
    WHERE slack_channel_id IS NOT NULL AND slack_message_ts IS NOT NULL;
