import { useEffect, useState } from 'react';
import api from './api';

const featureMenu = [
  { key: 'chatbot', label: 'Chatbot AI' },
  { key: 'pomodoro', label: 'Pomodoro' },
  { key: 'notes', label: 'Notes/Task' },
//   { key: 'schedule', label: 'Study Plan' }
];

function Dashboard({ user, onLogout }) {
  const [activeFeature, setActiveFeature] = useState('chatbot');
  const [chatInput, setChatInput] = useState('');
  const [chatReply, setChatReply] = useState('');
  const [noteInput, setNoteInput] = useState('');
  const [notes, setNotes] = useState([]);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDeadline, setTaskDeadline] = useState('');
  const [plan, setPlan] = useState([]);
  const [pomodoroMin, setPomodoroMin] = useState(25);
  const [remainingSec, setRemainingSec] = useState(25 * 60);
  const [isRunning, setIsRunning] = useState(false);
  const [message, setMessage] = useState('');

  const userId = user?._id;

  useEffect(() => {
    if (!isRunning) return undefined;

    const timer = setInterval(() => {
      setRemainingSec((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isRunning]);

  useEffect(() => {
    if (remainingSec === 0 && isRunning) {
      setIsRunning(false);
      setMessage('Pomodoro hoàn thành, nghỉ 5 phút nhé!');
    }
  }, [remainingSec, isRunning]);

  const sendChat = async () => {
    try {
      const res = await api.post('/ai/chat', { userId, message: chatInput });
      setChatReply(res.data.reply);
      setMessage('');
    } catch (err) {
      setMessage(err.response?.data?.message || err.message);
    }
  };

  const createNote = async () => {
    try {
      await api.post('/notes', { userId, content: noteInput });
      setNoteInput('');
      await fetchNotes();
      setMessage('Đã thêm note');
    } catch (err) {
      setMessage(err.response?.data?.message || err.message);
    }
  };

  const fetchNotes = async () => {
    try {
      const res = await api.get(`/notes/${userId}`);
      setNotes(res.data.notes || []);
      setMessage('');
    } catch (err) {
      setMessage(err.response?.data?.message || err.message);
    }
  };

  const addTask = async () => {
    try {
      await api.post('/schedule/task', {
        userId,
        title: taskTitle,
        deadline: taskDeadline
      });
      setTaskTitle('');
      setTaskDeadline('');
      setMessage('Đã thêm task');
    } catch (err) {
      setMessage(err.response?.data?.message || err.message);
    }
  };

  const generatePlan = async () => {
    try {
      const res = await api.get(`/schedule/generate/${userId}`);
      setPlan(res.data.plan || []);
      setMessage('');
    } catch (err) {
      setMessage(err.response?.data?.message || err.message);
    }
  };

  const resetPomodoro = () => {
    setIsRunning(false);
    setRemainingSec(Number(pomodoroMin) * 60);
  };

  const timeText = `${String(Math.floor(remainingSec / 60)).padStart(2, '0')}:${String(
    remainingSec % 60
  ).padStart(2, '0')}`;

  return (
    <div className="container">
      <h2>Dashboard</h2>
      <p>
        Xin chào <strong>{user?.name}</strong>
      </p>

      <div className="actions">
        <nav className="menu-list">
          {featureMenu.map((item) => (
            <button
              key={item.key}
              className={activeFeature === item.key ? 'menu-btn active' : 'menu-btn'}
              onClick={() => setActiveFeature(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <button className="menu-btn btn-danger" onClick={onLogout}>
          Đăng xuất
        </button>
      </div>

      <main>
        {activeFeature === 'chatbot' && (
          <section>
            <h2>Chatbot AI</h2>
            <textarea
              placeholder="Nhập câu hỏi học tập/tâm lý/nghề nghiệp"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
            />
            <button onClick={sendChat}>Gửi</button>
            {chatReply && <p className="reply">{chatReply}</p>}
          </section>
        )}

        {activeFeature === 'pomodoro' && (
          <section>
            <h2>Pomodoro</h2>
            <label>Số phút</label>
            <input
              type="number"
              min="1"
              value={pomodoroMin}
              onChange={(e) => setPomodoroMin(e.target.value)}
            />
            <p className="timer">{timeText}</p>
            <div className="row">
              <button onClick={() => setIsRunning(true)}>Start</button>
              <button onClick={() => setIsRunning(false)}>Pause</button>
              <button onClick={resetPomodoro}>Reset</button>
            </div>
          </section>
        )}

        {activeFeature === 'notes' && (
          <section>
            <h2>Thêm note/task</h2>
            <textarea
              placeholder="Ví dụ: Thứ 5 tuần sau 9h họp nhóm"
              value={noteInput}
              onChange={(e) => setNoteInput(e.target.value)}
            />
            <div className="row">
              <button onClick={createNote}>Thêm note</button>
              <button onClick={fetchNotes}>Tải note</button>
            </div>

            <input
              placeholder="Tên task"
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
            />
            <input
              type="datetime-local"
              value={taskDeadline}
              onChange={(e) => setTaskDeadline(e.target.value)}
            />
            <button onClick={addTask}>Thêm task</button>

            <ul>
              {notes.map((n) => (
                <li key={n._id}>
                  {n.content} {n.datetime ? `→ ${new Date(n.datetime).toLocaleString()}` : ''}
                </li>
              ))}
            </ul>
          </section>
        )}

        {activeFeature === 'schedule' && (
          <section>
            <h2>Study Plan cơ bản</h2>
            <button onClick={generatePlan}>Generate</button>
            <ul>
              {plan.map((item) => (
                <li key={item.taskId}>
                  {item.title} | slot: {item.suggestedSlot} | {item.strategy}
                </li>
              ))}
            </ul>
          </section>
        )}

        {message && <p className="message">{message}</p>}
      </main>
    </div>
  );
}

export default Dashboard;
