import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { handleProxy } from './proxy.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Serve static frontend
app.use(express.static(__dirname));

// Proxy endpoint for Guest Browser
app.get('/api/proxy', handleProxy);

app.listen(PORT, () => {
  console.log(`=========================================`);
  console.log(` 🍌 Banana OS running at http://localhost:${PORT}`);
  console.log(`=========================================`);
});