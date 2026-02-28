const express = require('express');
const chrono = require('chrono-node');
const Note = require('../models/Note');

const router = express.Router();

const parseDateTime = (content) => {
  if (!content) return null;

  const viParser = chrono.vi && typeof chrono.vi.parseDate === 'function'
    ? chrono.vi.parseDate.bind(chrono.vi)
    : null;

  if (viParser) {
    const viParsed = viParser(content);
    if (viParsed) return viParsed;
  }

  return chrono.parseDate(content);
};

router.post('/', async (req, res) => {
  try {
    const { userId, content, repeat } = req.body;

    if (!userId || !content) {
      return res.status(400).json({ message: 'userId và content là bắt buộc' });
    }

    const parsed = parseDateTime(content);

    const note = await Note.create({
      userId,
      content,
      datetime: parsed || null,
      repeat: repeat || 'none'
    });

    res.status(201).json({ note });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

router.get('/:userId', async (req, res) => {
  try {
    const notes = await Note.find({ userId: req.params.userId }).sort({ createdAt: -1 });
    res.json({ notes });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

module.exports = router;
