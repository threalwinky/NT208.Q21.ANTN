const mongoose = require('mongoose');

const taskSchema = new mongoose.Schema(
  {
    userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
    title: { type: String, required: true },
    deadline: { type: Date, required: true },
    status: { type: String, enum: ['todo', 'doing', 'done'], default: 'todo' }
  },
  { timestamps: true }
);

module.exports = mongoose.model('Task', taskSchema);
