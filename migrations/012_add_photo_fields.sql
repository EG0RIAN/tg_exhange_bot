-- Добавление полей для фото/документов в заявки
-- Это позволит пользователям прикреплять фото чеков, документов и т.п.

ALTER TABLE orders ADD COLUMN IF NOT EXISTS photo_file_id VARCHAR(255);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS photo_file_type VARCHAR(20);  -- photo, document

COMMENT ON COLUMN orders.photo_file_id IS 'Telegram file_id прикрепленного фото/документа';
COMMENT ON COLUMN orders.photo_file_type IS 'Тип файла: photo или document';

