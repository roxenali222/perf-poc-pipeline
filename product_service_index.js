/**
 * Product Service — with Dynatrace custom metrics
 * PORT: 3001
 */
const express = require('express');
const cors = require('cors');
const { dynatraceMiddleware, startMetricsCollection } = require('./dynatrace-metrics');

const app = express();
app.use(cors());
app.use(express.json());

// ← Dynatrace metrics middleware (add before routes)
app.use(dynatraceMiddleware);

const products = [
  { id: 1, name: 'Laptop Pro', price: 1299.99, category: 'Electronics', stock: 50, rating: 4.5 },
  { id: 2, name: 'Wireless Headphones', price: 199.99, category: 'Electronics', stock: 100, rating: 4.2 },
  { id: 3, name: 'Running Shoes', price: 89.99, category: 'Sports', stock: 200, rating: 4.7 },
  { id: 4, name: 'Coffee Maker', price: 149.99, category: 'Kitchen', stock: 75, rating: 4.3 },
  { id: 5, name: 'Smart Watch', price: 299.99, category: 'Electronics', stock: 80, rating: 4.6 },
];

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'product-service' });
});

app.get('/api/products', (req, res) => {
  res.json({ total: products.length, products });
});

app.get('/api/products/search', (req, res) => {
  const { q } = req.query;
  const results = products.filter(p =>
    p.name.toLowerCase().includes((q || '').toLowerCase())
  );
  res.json({ products: results });
});

app.get('/api/products/:id', (req, res) => {
  const product = products.find(p => p.id === parseInt(req.params.id));
  if (!product) return res.status(404).json({ error: 'Not found' });
  res.json(product);
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Product Service running on port ${PORT}`);
  // Start background metrics collection every 30s
  startMetricsCollection(30000);
});
