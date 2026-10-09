import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! 👋 I'm the Schools Universe AI Assistant. How can I help you today?",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const question = input.trim();

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: question,
      },
    ]);

    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question,
          session_id: "frontend-session-001",
        }),
      });

      if (!response.ok) {
        throw new Error("Backend API request failed");
      }

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.llm_response,
          responseType: data.response_type,
          schools: data.schools || [],
          ragResults: data.rag_results || [],
          sources: data.sources || [],
          schoolName: data.school_name || null,
        },
      ]);
    } catch (error) {
      console.error("API Error:", error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I couldn't connect to the AI Assistant. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
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

              <div className="message-content">

                {/* Normal answer */}
                {message.content && (
                  <div className="message">
                    {message.content}
                  </div>
                )}

                {/* School Cards */}
                {message.role === "assistant" &&
                  message.schools &&
                  message.schools.length > 0 && (
                    <div className="school-section">
                      <h3>🏫 Schools</h3>

                      <div className="school-grid">
                        {message.schools.map((school) => (
                          <div
                            className="school-card"
                            key={school.id}
                          >
                            <h3>{school.name}</h3>

                            {school.address && (
                              <p>
                                <strong>📍 Address:</strong>{" "}
                                {school.address}
                              </p>
                            )}

                            {school.city && (
                              <p>
                                <strong>🏙️ City:</strong>{" "}
                                {school.city}
                              </p>
                            )}

                            {school.state && (
                              <p>
                                <strong>📌 State:</strong>{" "}
                                {school.state}
                              </p>
                            )}

                            {school.phone && (
                              <p>
                                <strong>📞 Phone:</strong>{" "}
                                {school.phone}
                              </p>
                            )}

                            {school.email && (
                              <p>
                                <strong>✉️ Email:</strong>{" "}
                                {school.email}
                              </p>
                            )}

                            {school.website && (
                              <a
                                href={school.website}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="website-button"
                              >
                                🌐 Visit Website
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                {/* RAG Sources */}
                {message.role === "assistant" &&
                  message.sources &&
                  message.sources.length > 0 && (
                    <div className="sources-section">
                      <h3>📚 Sources</h3>

                      {message.sources.map((source, sourceIndex) => (
                        <div
                          className="source-card"
                          key={sourceIndex}
                        >
                          <p>
                            📄 Document ID:{" "}
                            {source.document_id}
                          </p>

                          <p>
                            🏫 School ID:{" "}
                            {source.school_id}
                          </p>

                          {source.page_number && (
                            <p>
                              📖 Page:{" "}
                              {source.page_number}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
              </div>
            </div>
          ))}

          {/* Loading */}
          {loading && (
            <div className="message-row assistant">
              <div className="avatar">🤖</div>

              <div className="message">
                Thinking...
              </div>
            </div>
          )}
        </main>

        {/* Input */}
        <div className="chat-input-area">
          <input
            type="text"
            placeholder="Ask about schools, admissions, fees, facilities..."
            value={input}
            disabled={loading}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                sendMessage();
              }
            }}
          />

          <button
            onClick={sendMessage}
            disabled={loading}
          >
            {loading ? "..." : "Send"}
          </button>
        </div>

      </div>
    </div>
  );
}

export default App;