// MongoDB initialization script
// Create database and user
db = db.getSiblingDB('sampledb');

// Create user with read/write access to sampledb
db.createUser({
  user: "appuser",
  pwd: "apppassword",
  roles: [
    {
      role: "readWrite",
      db: "sampledb"
    }
  ]
});

// Sample collections and data
db.users.insertMany([
  {
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30,
    "department": "Engineering",
    "hire_date": new Date("2023-01-15"),
    "salary": 85000,
    "active": true
  },
  {
    "name": "Jane Smith",
    "email": "jane@example.com",
    "age": 28,
    "department": "Marketing",
    "hire_date": new Date("2023-03-20"),
    "salary": 72000,
    "active": true
  },
  {
    "name": "Bob Johnson",
    "email": "bob@example.com",
    "age": 35,
    "department": "Sales",
    "hire_date": new Date("2022-08-10"),
    "salary": 68000,
    "active": false
  },
  {
    "name": "Alice Brown",
    "email": "alice@example.com",
    "age": 32,
    "department": "Engineering",
    "hire_date": new Date("2023-06-01"),
    "salary": 92000,
    "active": true
  }
]);

db.orders.insertMany([
  {
    "order_id": "ORD-001",
    "customer_name": "John Doe",
    "product": "Laptop",
    "quantity": 2,
    "price": 1500.00,
    "order_date": new Date("2024-01-15"),
    "status": "delivered"
  },
  {
    "order_id": "ORD-002",
    "customer_name": "Jane Smith",
    "product": "Mouse",
    "quantity": 5,
    "price": 25.00,
    "order_date": new Date("2024-01-20"),
    "status": "pending"
  },
  {
    "order_id": "ORD-003",
    "customer_name": "Bob Johnson",
    "product": "Keyboard",
    "quantity": 1,
    "price": 75.00,
    "order_date": new Date("2024-01-25"),
    "status": "shipped"
  }
]);

print("Sample data inserted successfully!");
