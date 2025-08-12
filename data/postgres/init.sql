-- PostgreSQL initialization script
-- Create sample tables and data for testing

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    age INTEGER,
    department VARCHAR(50),
    hire_date DATE,
    salary DECIMAL(10,2),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(100),
    product VARCHAR(100),
    quantity INTEGER,
    price DECIMAL(10,2),
    order_date DATE,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price DECIMAL(10,2),
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO users (name, email, age, department, hire_date, salary, active) VALUES
    ('John Doe', 'john@example.com', 30, 'Engineering', '2023-01-15', 85000.00, TRUE),
    ('Jane Smith', 'jane@example.com', 28, 'Marketing', '2023-03-20', 72000.00, TRUE),
    ('Bob Johnson', 'bob@example.com', 35, 'Sales', '2022-08-10', 68000.00, FALSE),
    ('Alice Brown', 'alice@example.com', 32, 'Engineering', '2023-06-01', 92000.00, TRUE),
    ('Charlie Wilson', 'charlie@example.com', 29, 'HR', '2023-02-10', 65000.00, TRUE)
ON CONFLICT (email) DO NOTHING;

INSERT INTO orders (order_id, customer_name, product, quantity, price, order_date, status) VALUES
    ('ORD-001', 'John Doe', 'Laptop', 2, 1500.00, '2024-01-15', 'delivered'),
    ('ORD-002', 'Jane Smith', 'Mouse', 5, 25.00, '2024-01-20', 'pending'),
    ('ORD-003', 'Bob Johnson', 'Keyboard', 1, 75.00, '2024-01-25', 'shipped'),
    ('ORD-004', 'Alice Brown', 'Monitor', 1, 350.00, '2024-01-10', 'delivered'),
    ('ORD-005', 'John Doe', 'Webcam', 1, 120.00, CURRENT_DATE - INTERVAL '1 day', 'pending')
ON CONFLICT (order_id) DO NOTHING;

INSERT INTO products (name, category, price, stock_quantity) VALUES
    ('Laptop', 'Electronics', 1500.00, 50),
    ('Mouse', 'Accessories', 25.00, 200),
    ('Keyboard', 'Accessories', 75.00, 150),
    ('Monitor', 'Electronics', 350.00, 75),
    ('Webcam', 'Electronics', 120.00, 100)
ON CONFLICT DO NOTHING;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_department ON users(department);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(active);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
