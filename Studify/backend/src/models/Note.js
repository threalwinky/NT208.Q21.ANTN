const mongoose = require('mongoose');

const noteSchema = new mongoose.Schema(
  {
    userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
    content: { type: String, required: true },
    datetime: { type: Date },
    repeat: { type: String, default: 'none' },
    reminderSent: { type: Boolean, default: false }
  },
  { timestamps: true }
);

module.exports = mongoose.model('Note', noteSchema);
