const mongoose = require('mongoose');

const userSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    email: { type: String, required: true, unique: true },
    password: { type: String, required: true },
    university: { type: String, default: '' },
    major: { type: String, default: '' },
    year: { type: String, default: '' },
    gpaTarget: { type: String, default: '' },
    careerGoal: { type: String, default: '' },
    studyHabits: { type: String, default: '' },
    freeTimeSlots: [{ type: String }]
  },
  { timestamps: true }
);

module.exports = mongoose.model('User', userSchema);
