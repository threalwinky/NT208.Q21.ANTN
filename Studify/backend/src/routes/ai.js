const express = require('express');
const axios = require('axios');
const User = require('../models/User');

const router = express.Router();

router.post('/chat', async (req, res) => {
  try {
    const { userId, message } = req.body;

    if (!userId || !message) {
      return res.status(400).json({ message: 'userId và message là bắt buộc' });
    }

    const user = await User.findById(userId).lean();
    if (!user) {
      return res.status(404).json({ message: 'Không tìm thấy user' });
    }

    const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://ai:8000';
    const aiResponse = await axios.post(`${aiServiceUrl}/chat`, {
      message,
      profile: {
        name: user.name,
        major: user.major,
        year: user.year,
        careerGoal: user.careerGoal,
        studyHabits: user.studyHabits,
        gpaTarget: user.gpaTarget
      }
    });

    res.json(aiResponse.data);
  } catch (error) {
    const message = error.response?.data?.detail || error.message;
    res.status(500).json({ message });
  }
});

module.exports = router;
