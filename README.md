Пока вы скачиваете макеты, я подготовил структуру базы данных (SQL) для вашей команды, которую просили. Ваши бэкендеры могут просто скопировать этот текст и закинуть Клоду со словами: «Разверни БД на PostgreSQL/MySQL по этой структуре макетов нашего дизайнера».
-- Таблица пользователей (Экран Профиль)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) DEFAULT 'Саныч',
    email VARCHAR(150) UNIQUE NOT NULL,
    google_linked BOOLEAN DEFAULT TRUE,
    apple_linked BOOLEAN DEFAULT FALSE,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    autosave_enabled BOOLEAN DEFAULT TRUE,
    biometrics_enabled BOOLEAN DEFAULT FALSE,
    theme_preference VARCHAR(10) DEFAULT 'light' -- 'light' or 'dark'
);

-- Таблица чеков (Экран Камера и История)
CREATE TABLE receipts (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    shop_name VARCHAR(150) NOT NULL, -- Например, 'Евроопт'
    date_timestamp TIMESTAMP NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL, -- Сумма чека, например, 1240.00
    currency VARCHAR(10) DEFAULT 'Br',
    category_name VARCHAR(100) NOT NULL -- Например, 'Продукты' или 'Транспорт'
);

-- Detalization: Позиции внутри конкретного чека (Шторка детализации)
CREATE TABLE receipt_items (
    id SERIAL PRIMARY KEY,
    receipt_id INT REFERENCES receipts(id) ON DELETE CASCADE,
    item_name VARCHAR(200) NOT NULL, -- 'Хлеб', 'Молоко', 'Сыр'
    price NUMERIC(10, 2) NOT NULL
);
