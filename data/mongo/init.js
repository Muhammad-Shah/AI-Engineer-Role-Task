// Initialize MongoDB with application user and sample data
db = db.getSiblingDB('sampledb');

// Create app user with readWrite on sampledb
db.createUser({
  user: 'appuser',
  pwd: 'apppassword',
  roles: [{ role: 'readWrite', db: 'sampledb' }]
});

// Sample collections and documents
db.users.insertMany([
  { name: 'Alice', email: 'alice@example.com', created_at: new Date(Date.now() - 40*24*60*60*1000) },
  { name: 'Bob', email: 'bob@example.com', created_at: new Date(Date.now() - 20*24*60*60*1000) },
  { name: 'Carol', email: 'carol@example.com', created_at: new Date(Date.now() - 10*24*60*60*1000) },
  { name: 'Dave', email: 'dave@example.com', created_at: new Date(Date.now() - 1*24*60*60*1000) }
]);

db.orders.insertMany([
  { user_email: 'alice@example.com', amount: 120.50, order_date: new Date(Date.now() - 35*24*60*60*1000) },
  { user_email: 'bob@example.com', amount: 75.00, order_date: new Date(Date.now() - 15*24*60*60*1000) },
  { user_email: 'bob@example.com', amount: 33.40, order_date: new Date(Date.now() - 8*24*60*60*1000) },
  { user_email: 'carol@example.com', amount: 220.10, order_date: new Date(Date.now() - 2*24*60*60*1000) },
  { user_email: 'dave@example.com', amount: 15.99, order_date: new Date(Date.now() - 12*60*60*1000) }
]);


