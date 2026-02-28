const express = require('express');
const User = require('../models/User');

const router = express.Router();

router.post('/register', async (req, res) => {
  try {
    const {
      name,
      email,
      password,
      university,
      major,
      year,
      gpaTarget,
      careerGoal,
      studyHabits,
      freeTimeSlots
    } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({ message: 'name, email, password là bắt buộc' });
    }

    const existing = await User.findOne({ email });
    if (existing) {
      return res.status(409).json({ message: 'Email đã tồn tại' });
    }

    const user = await User.create({
      name,
      email,
      password,
      university,
      major,
      year,
      gpaTarget,
      careerGoal,
      studyHabits,
      freeTimeSlots: Array.isArray(freeTimeSlots) ? freeTimeSlots : []
    });

    res.status(201).json({ user });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ message: 'email và password là bắt buộc' });
    }

    const user = await User.findOne({ email });
    if (!user || user.password !== password) {
      return res.status(401).json({ message: 'Sai email hoặc mật khẩu' });
    }

    res.json({ user });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

module.exports = router;
