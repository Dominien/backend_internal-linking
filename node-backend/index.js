const express = require('express');
const bodyParser = require('body-parser');
const jwt = require('jsonwebtoken');
const cors = require('cors');

const app = express();
app.use(bodyParser.json());
app.use(cors());

const secretKey = 'your-secret-key';  // Store secret key in a variable

const validKeys = {
  '123456789101': { user: 'User1', expires: '2024-12-31' },
  '111122223333': { user: 'User2', expires: '2024-12-31' },
};

// Normalize the product key by removing any dashes
function normalizeKey(key) {
  return key.replace(/-/g, '');
}

// Middleware to authenticate and verify the token
function authenticateToken(req, res, next) {
  const token = req.body.token;

  if (!token) return res.status(401).json({ valid: false, error: 'Token is required' });

  jwt.verify(token, secretKey, (err, decoded) => {
    if (err) return res.status(401).json({ valid: false, error: 'Token is invalid or has expired' });

    req.decoded = decoded;
    next();
  });
}

// Endpoint to validate the product key and generate a token
app.post('/api/validate-key', (req, res) => {
  const { productKey } = req.body;
  const normalizedKey = normalizeKey(productKey);

  const keyData = validKeys[normalizedKey];

  if (keyData) {
    const token = jwt.sign({ productKey: normalizedKey, user: keyData.user }, secretKey, { expiresIn: '30d' });
    res.json({ token });
  } else {
    res.status(401).json({ error: 'Invalid product key' });
  }
});

// Endpoint to validate the token
app.post('/api/validate-token', authenticateToken, (req, res) => {
  res.json({ valid: true });
});

// Endpoint to get user details based on the token
app.post('/api/get-user', authenticateToken, (req, res) => {
  const { productKey } = req.decoded;
  const keyData = validKeys[productKey];

  if (keyData) {
    res.json({ valid: true, user: keyData.user });
  } else {
    res.status(401).json({ valid: false, error: 'User not found for the provided token' });
  }
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
