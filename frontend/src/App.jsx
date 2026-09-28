import { useState } from "react";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! 👋 I'm the Schools Universe AI Assistant. How can I help you today?",
    },
  ]);

  const [input, setInput] = useState("");

  const sendMessage = () => {
    if (!input.trim()) return;

    const userMessage = {
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    // Backend connection will be added next.
  };

  return (
    <div className="app">
      <div className="chat-container">

        {/* Header */}
        <header className="chat-header">
          <div className="logo">🏫</div>

          <div>
            <h1>Schools Universe AI</h1>
            <p>School Information Assistant</p>
          </div>

          <div className="status">
            <span></span>
            Online
          </div>
        </header>

        {/* Messages */}
        <main className="chat-messages">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`message-row ${message.role}`}
            >
              <div className="avatar">
                {message.role === "assistant" ? "🤖" : "👤"}
              </div>

              <div className="message">
                {message.content}
              </div>
            </div>
          ))}
        </main>

        {/* Input */}
        <div className="chat-input-area">
          <input
            type="text"
            placeholder="Ask about schools, admissions, fees, facilities..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                sendMessage();
              }
            }}
          />

          <button onClick={sendMessage}>
            Send
          </button>
        </div>

      </div>
    </div>
  );
}

export default App;