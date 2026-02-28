require('dotenv').config();
const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');

const authRoutes = require('./routes/auth');
const aiRoutes = require('./routes/ai');
const noteRoutes = require('./routes/notes');
const scheduleRoutes = require('./routes/schedule');

const app = express();

app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ ok: true, service: 'backend' });
});

app.use('/api/auth', authRoutes);
app.use('/api/ai', aiRoutes);
app.use('/api/notes', noteRoutes);
app.use('/api/schedule', scheduleRoutes);

const port = process.env.PORT || 5000;
const mongoUri = process.env.MONGO_URI || 'mongodb://db:27017/studify';

mongoose
  .connect(mongoUri)
  .then(() => {
    app.listen(port, () => {
      console.log(`Backend running on port ${port}`);
    });
  })
  .catch((error) => {
    console.error('Mongo connect error:', error.message);
    process.exit(1);
  });