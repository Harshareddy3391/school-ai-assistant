
import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const THEMES = {
  ocean: {
    name: "Ocean Blue",
    emoji: "🌊",
    accent: "#4779f5",
    accent2: "#7857e8",
    bg: "#f4f7fc",
    panel: "#ffffff",
    text: "#25314a",
    muted: "#8993a8",
    bubble: "#f0f3ff",
    border: "#e5eaf4",
    userText: "#ffffff",
  },
  midnight: {
    name: "Midnight Dark",
    emoji: "🌙",
    accent: "#6366f1",
    accent2: "#8b5cf6",
    bg: "#111827",
    panel: "#1f2937",
    text: "#f3f4f6",
    muted: "#aab5c8",
    bubble: "#253248",
    border: "#374151",
    userText: "#ffffff",
  },
  emerald: {
    name: "Emerald Green",
    emoji: "🌿",
    accent: "#059669",
    accent2: "#10b981",
    bg: "#f0faf5",
    panel: "#ffffff",
    text: "#183d32",
    muted: "#66877a",
    bubble: "#e5f6ed",
    border: "#d4eadf",
    userText: "#ffffff",
  },
  sunset: {
    name: "Sunset Purple",
    emoji: "🌅",
    accent: "#8b5cf6",
    accent2: "#d946ef",
    bg: "#faf5ff",
    panel: "#ffffff",
    text: "#38254f",
    muted: "#8b7b9e",
    bubble: "#f3e8ff",
    border: "#eadcf8",
    userText: "#ffffff",
  },
  rose: {
    name: "Rose Pink",
    emoji: "🌸",
    accent: "#e64980",
    accent2: "#f472b6",
    bg: "#fff5f7",
    panel: "#ffffff",
    text: "#512b3a",
    muted: "#a17b8a",
    bubble: "#ffe4ec",
    border: "#f6d8e2",
    userText: "#ffffff",
  },
};
 


const INITIAL_MESSAGE = {
  role: "assistant",
  content:
    "Hi there! 👋 I'm ZUZU, your friendly Schools Universe buddy! 🐣 I can help you discover schools, explore admissions, and find school fee information. What would you like to know?",
  time: new Date(),
};


function App() {
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [thinkingText, setThinkingText] = useState(
    "Understanding your question"
  );
  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem("school-chat-theme");
      return saved && THEMES[saved] ? saved : "ocean";
    } catch {
      return "ocean";
    }
  });
  const [themeMenuOpen, setThemeMenuOpen] = useState(false);

  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const themePickerRef = useRef(null);

  // Apply the selected theme across the whole interface.
  useEffect(() => {
    const selectedTheme = THEMES[theme] || THEMES.ocean;
    const root = document.documentElement;

    Object.entries(selectedTheme).forEach(([key, value]) => {
      if (
        ["accent", "accent2", "bg", "panel", "text",
          "muted", "bubble", "border", "userText"].includes(key)
      ) {
        root.style.setProperty(`--theme-${key}`, value);
      }
    });

    try {
      localStorage.setItem("school-chat-theme", theme);
    } catch {
      // The interface still works if browser storage is unavailable.
    }
  }, [theme]);

  // Scroll to the newest message when the conversation changes.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, loading, thinkingText]);

  // Rotate the thinking status while the backend is processing.
  useEffect(() => {
    if (!loading) return;

    const statuses = [
      "Understanding your question",
      "Searching school information",
      "Preparing your answer",
    ];

    let index = 0;
    setThinkingText(statuses[0]);

    const interval = setInterval(() => {
      index = (index + 1) % statuses.length;
      setThinkingText(statuses[index]);
    }, 1800);

    return () => clearInterval(interval);
  }, [loading]);

  // Close the theme menu when clicking outside it.
  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (
        themePickerRef.current &&
        !themePickerRef.current.contains(event.target)
      ) {
        setThemeMenuOpen(false);
      }
    };

    document.addEventListener("pointerdown", handleOutsideClick);

    return () => {
      document.removeEventListener("pointerdown", handleOutsideClick);
    };
  }, []);

  const formatTime = (date) =>
    new Date(date).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

  const sendMessage = async (customQuestion) => {
    const question = (customQuestion ?? input).trim();

    if (!question || loading) return;

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: question,
        time: new Date(),
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
          question,
          session_id: "frontend-session-001",
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat API request failed: ${response.status}`);
      }

      const data = await response.json();

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            data.llm_response || "I couldn't generate an answer.",
          responseType: data.response_type,
          schools: data.schools || [],
          time: new Date(),
        },
      ]);
    } catch (error) {
      console.error("Chat API error:", error);

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            "I'm having trouble connecting right now. Please check that the backend is running and try again.",
          time: new Date(),
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const selectedTheme = THEMES[theme] || THEMES.ocean;

  return (
    <div className="app-shell">
      <div className="chat-container">
        <header className="chat-header">
          <div className="brand">
            <div className="brand-logo">
              <span>✦</span>
            </div>

            <div className="brand-copy">
              
<h1>Schools Universe</h1>
<p>Chat with ZUZU ✨</p>

            </div>
          </div>

          <div className="header-actions">
            <div className="online-status">
              <span className="online-dot" />
              <span>AI Assistant</span>
            </div>

            <div className="theme-picker" ref={themePickerRef}>
              <button
                type="button"
                className="theme-picker-button"
                onClick={() => setThemeMenuOpen((open) => !open)}
                aria-expanded={themeMenuOpen}
                aria-haspopup="menu"
                aria-label="Customize chatbot theme"
              >
                <span className="palette-icon">🎨</span>
                <span className="theme-button-label">Theme</span>
                <span className="theme-chevron">
                  {themeMenuOpen ? "⌃" : "⌄"}
                </span>
              </button>

              {themeMenuOpen && (
                <div className="theme-menu" role="menu">
                  <div className="theme-menu-heading">
                    <strong>Personalize your chat</strong>
                    <span>Choose a color theme</span>
                  </div>

                  {Object.entries(THEMES).map(([key, item]) => (
                    <button
                      type="button"
                      key={key}
                      role="menuitemradio"
                      aria-checked={theme === key}
                      className={`theme-option ${
                        theme === key ? "active" : ""
                      }`}
                      onClick={() => {
                        setTheme(key);
                        setThemeMenuOpen(false);
                      }}
                    >
                      <span
                        className="theme-swatch"
                        style={{
                          background: `linear-gradient(135deg, ${item.accent}, ${item.accent2})`,
                        }}
                      />

                      <span className="theme-option-name">
                        {item.emoji} {item.name}
                      </span>

                      {theme === key && (
                        <span className="theme-check">✓</span>
                      )}
                    </button>
                  ))}

                  <div className="theme-menu-footer">
                    Theme preference is saved on this browser.
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="chat-messages">
          <div className="welcome-label">
            <span className="welcome-star">✦</span>
            Your personal school guide
          </div>

          {messages.map((message, index) => (
            <div
              key={`${index}-${message.role}`}
              className={`message-row ${message.role}`}
            >
              {message.role === "assistant" && (
                <div className="assistant-avatar">✦</div>
              )}

              <div className="message-content">
                <div
                  className={`message-bubble ${
                    message.role === "user"
                      ? "user-bubble"
                      : "bot-bubble"
                  } ${message.isError ? "error-bubble" : ""}`}
                >
                  <div className="message-text">{message.content}</div>
                </div>

                {message.role === "assistant" &&
                  message.schools?.length > 0 && (
                    <section className="school-section">
                      <div className="section-heading">
                        <div className="section-icon">🏫</div>
                        <div>
                          <h2>Schools for you</h2>
                          <p>
                            {message.schools.length} schools found
                          </p>
                        </div>
                      </div>

                      <div className="school-grid">
                        {message.schools.map((school) => (
                          <article
                            className="school-card"
                            key={school.id}
                          >
                            <div className="school-card-top">
                              <div className="school-icon">🏫</div>
                              <span className="school-tag">
                                School
                              </span>
                            </div>

                            <h3>{school.name}</h3>

                            {(school.city || school.state) && (
                              <p className="school-detail">
                                <span>📍</span>
                                <span>
                                  {[school.city, school.state]
                                    .filter(Boolean)
                                    .join(", ")}
                                </span>
                              </p>
                            )}

                            {school.address && (
                              <p className="school-detail">
                                <span>🗺️</span>
                                <span>{school.address}</span>
                              </p>
                            )}

                            {school.phone && (
                              <p className="school-detail">
                                <span>📞</span>
                                <span>{school.phone}</span>
                              </p>
                            )}

                            {school.email && (
                              <p className="school-detail">
                                <span>✉️</span>
                                <span>{school.email}</span>
                              </p>
                            )}

                            {school.website && (
                              <a
                                className="school-link"
                                href={school.website}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                Visit website <span>↗</span>
                              </a>
                            )}
                          </article>
                        ))}
                      </div>
                    </section>
                  )}

                <div className="message-meta">
                  <span>
                    {message.role === "assistant"
                      ? "School AI"
                      : "You"}
                  </span>
                  <span className="meta-dot">·</span>
                  <span>{formatTime(message.time)}</span>
                </div>
              </div>

              {message.role === "user" && (
                <div className="user-avatar">You</div>
              )}
            </div>
          ))}

          {loading && (
            <div className="message-row assistant thinking-row">
              <div className="assistant-avatar thinking-avatar">
                ✦
              </div>

              <div className="message-content">
                <div className="thinking-bubble">
                  <div
                    className="thinking-dots"
                    aria-label="Assistant is thinking"
                  >
                    <span />
                    <span />
                    <span />
                  </div>

                  <span className="thinking-label" key={thinkingText}>
                    {thinkingText}
                  </span>
                </div>

                <div className="thinking-caption">
                  Please wait a moment
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </main>

        <footer className="chat-footer">

          <form
            className="chat-input-area"
            onSubmit={(event) => {
              event.preventDefault();
              sendMessage();
            }}
          >
            <input
              ref={inputRef}
              type="text"
              placeholder="Ask anything about schools..."
              value={input}
              disabled={loading}
              onChange={(event) => setInput(event.target.value)}
              aria-label="Your message"
            />

            <button
              className="send-button"
              type="submit"
              disabled={loading || !input.trim()}
              aria-label="Send message"
            >
              <span>{loading ? "…" : "➤"}</span>
            </button>
          </form>

          <p className="footer-note">
            AI-generated answers may need confirmation from the school.
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
