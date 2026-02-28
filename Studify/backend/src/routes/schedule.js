const express = require('express');
const Task = require('../models/Task');
const User = require('../models/User');

const router = express.Router();

router.post('/task', async (req, res) => {
  try {
    const { userId, title, deadline } = req.body;

    if (!userId || !title || !deadline) {
      return res.status(400).json({ message: 'userId, title, deadline là bắt buộc' });
    }

    const task = await Task.create({ userId, title, deadline });
    res.status(201).json({ task });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

router.get('/generate/:userId', async (req, res) => {
  try {
    const user = await User.findById(req.params.userId).lean();
    if (!user) {
      return res.status(404).json({ message: 'Không tìm thấy user' });
    }

    const tasks = await Task.find({ userId: req.params.userId, status: { $ne: 'done' } })
      .sort({ deadline: 1 })
      .lean();

    const slots = user.freeTimeSlots?.length ? user.freeTimeSlots : ['19:00-21:00'];

    const plan = tasks.slice(0, 7).map((task, index) => ({
      taskId: task._id,
      title: task.title,
      deadline: task.deadline,
      suggestedSlot: slots[index % slots.length],
      strategy: 'Pomodoro 50/10'
    }));

    res.json({ plan });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

module.exports = router;
