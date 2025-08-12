-- Sample schema and data for PostgreSQL
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    amount NUMERIC(10,2) NOT NULL,
    order_date TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Seed users
INSERT INTO users (name, email, created_at) VALUES
('Alice', 'alice@example.com', NOW() - INTERVAL '40 days'),
('Bob', 'bob@example.com', NOW() - INTERVAL '20 days'),
('Carol', 'carol@example.com', NOW() - INTERVAL '10 days'),
('Dave', 'dave@example.com', NOW() - INTERVAL '1 day')
ON CONFLICT DO NOTHING;

-- Seed orders
INSERT INTO orders (user_id, amount, order_date) VALUES
(1, 120.50, NOW() - INTERVAL '35 days'),
(2, 75.00, NOW() - INTERVAL '15 days'),
(2, 33.40, NOW() - INTERVAL '8 days'),
(3, 220.10, NOW() - INTERVAL '2 days'),
(4, 15.99, NOW() - INTERVAL '12 hours');
