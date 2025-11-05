-- Add FILE endpoint columns to systemendpoint for file-based message import

ALTER TABLE systemendpoint ADD COLUMN inbox_path TEXT;
ALTER TABLE systemendpoint ADD COLUMN outbox_path TEXT;
ALTER TABLE systemendpoint ADD COLUMN archive_path TEXT;
ALTER TABLE systemendpoint ADD COLUMN error_path TEXT;
ALTER TABLE systemendpoint ADD COLUMN file_extensions TEXT;
