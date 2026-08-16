## order-service/index.js mein add karo:

```javascript
// Add this endpoint - ViewCart was missing!
app.get('/api/cart', (req, res) => {
  res.json({
    cart_id: 'cart_001',
    items: [],
    total: 0,
    message: 'Cart retrieved successfully'
  });
});
```

Add this BEFORE the listen() line.
Then rebuild:
docker build -t your-registry.azurecr.io/order-service:latest ./services/order-service
docker push your-registry.azurecr.io/order-service:latest
kubectl rollout restart deployment/order-service