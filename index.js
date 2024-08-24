const express = require('express');
const bodyParser = require('body-parser');
const jwt = require('jsonwebtoken');
const cors = require('cors');

const app = express();
app.use(bodyParser.json());
app.use(cors());

const validKeys = {
  '123456789101': { user: 'User1', expires: '2024-12-31' }, // Normalize keys (remove dashes)
  '111122223333': { user: 'User2', expires: '2024-12-31' },
};

// Endpoint to validate the product key and generate a token
app.post('/api/validate-key', (req, res) => {
  const { productKey } = req.body;

  // Normalize the product key by removing any dashes
  const normalizedKey = productKey.replace(/-/g, '');

  const keyData = validKeys[normalizedKey];

  if (keyData) {
    const token = jwt.sign({ productKey: normalizedKey, user: keyData.user }, 'your-secret-key', { expiresIn: '30d' });
    res.json({ token });
  } else {
    res.status(401).json({ error: 'Invalid product key' });
  }
});

// New endpoint to validate the token
app.post('/api/validate-token', (req, res) => {
  const { token } = req.body;

  jwt.verify(token, 'your-secret-key', (err, decoded) => {
    if (err) {
      return res.status(401).json({ valid: false, error: 'Token is invalid or has expired' });
    }

    const keyData = validKeys[decoded.productKey];
    if (!keyData) {
      return res.status(401).json({ valid: false, error: 'Token does not match a valid product key' });
    }

    res.json({ valid: true });
  });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
