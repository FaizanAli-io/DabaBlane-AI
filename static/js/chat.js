// Chat Module
const Chat = {
  elements: {},

  init() {
    this.elements = {
      chatHistory: document.getElementById("chatHistory"),
      chatForm: document.getElementById("chatForm"),
      messageInput: document.getElementById("messageInput"),
      envSelect: document.getElementById("envSelect"),
      sessionIdSelect: document.getElementById("sessionId"),
      clearHistoryBtn: document.getElementById("clearHistoryBtn"),
      clearAllHistoryBtn: document.getElementById("clearAllHistoryBtn")
    };

    this.attachEventListeners();
    this.loadSessions().then(() => {
      setTimeout(() => {
        this.loadChatHistory();
      }, 100);
    });
  },

  attachEventListeners() {
    // Session change
    this.elements.sessionIdSelect.addEventListener("change", () => {
      this.loadChatHistory();
    });

    // Environment change
    this.elements.envSelect.addEventListener("change", async () => {
      await this.loadSessions();
      setTimeout(() => {
        this.loadChatHistory();
      }, 100);
    });

    // Clear single chat history
    this.elements.clearHistoryBtn.addEventListener("click", async () => {
      const session_id = this.elements.sessionIdSelect.value.trim();
      if (!session_id) {
        alert("Please select a session first");
        return;
      }

      const baseUrl = this.elements.envSelect.value;
      try {
        await fetch(`${baseUrl}/chat/history/${session_id}`, {
          method: "DELETE"
        });
        this.elements.chatHistory.innerHTML = "";
      } catch (err) {
        console.error("Error clearing chat history", err);
      }
    });

    // Clear all chat histories
    this.elements.clearAllHistoryBtn.addEventListener("click", async () => {
      if (
        !confirm("This will clear chat history for ALL sessions. Continue?")
      ) {
        return;
      }

      const baseUrl = this.elements.envSelect.value;
      try {
        await fetch(`${baseUrl}/chat/history`, { method: "DELETE" });
        this.elements.chatHistory.innerHTML = "";
        await this.loadSessions();
        setTimeout(() => {
          this.loadChatHistory();
        }, 100);
      } catch (err) {
        console.error("Error clearing all chat histories", err);
      }
    });

    // Message input - Shift+Enter for new line, Enter to send
    this.elements.messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.elements.chatForm.requestSubmit();
      }
    });

    // Chat form submit
    this.elements.chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const message = this.elements.messageInput.value.trim();
      if (!message) return;

      const session_id = this.elements.sessionIdSelect.value.trim();
      if (!session_id) {
        alert("Please select a session first");
        return;
      }

      this.appendMessage("user", message);
      this.elements.messageInput.value = "";

      const baseUrl = this.elements.envSelect.value;
      try {
        const res = await fetch(`${baseUrl}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id, message })
        });
        const data = await res.json();
        this.appendMessage("bot", data.response || "[No response]");
      } catch (err) {
        this.appendMessage("bot", "[Error connecting to agent]");
      }
    });
  },

  async loadSessions() {
    const baseUrl = this.elements.envSelect.value;
    try {
      const res = await fetch(`${baseUrl}/session/list`);
      const sessions = await res.json();

      // Clear existing options except the first one
      this.elements.sessionIdSelect.innerHTML =
        '<option value="">Select a session...</option>';

      // Add sessions to dropdown
      if (Array.isArray(sessions)) {
        sessions.forEach((session) => {
          const option = document.createElement("option");
          option.value = session.id || session;
          option.textContent = `${session.id || session} ${
            session.client_email ? "(" + session.client_email + ")" : ""
          }`;
          this.elements.sessionIdSelect.appendChild(option);
        });
      }
    } catch (error) {
      console.error("Error loading sessions:", error);
    }
  },

  appendMessage(sender, text) {
    const div = document.createElement("div");
    div.className = sender === "user" ? "msg-user" : "msg-bot";
    const msgSpan = document.createElement("span");
    msgSpan.className = "msg";
    msgSpan.textContent = text;
    div.appendChild(msgSpan);
    this.elements.chatHistory.appendChild(div);
    this.elements.chatHistory.scrollTop =
      this.elements.chatHistory.scrollHeight;
  },

  loadChatHistory() {
    this.elements.chatHistory.innerHTML = "";
    const session_id = this.elements.sessionIdSelect.value.trim();
    if (!session_id) return;

    const baseUrl = this.elements.envSelect.value;
    fetch(`${baseUrl}/chat/history/${session_id}`)
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          data.forEach((msg) => this.appendMessage(msg.sender, msg.message));
        }
      })
      .catch((err) => {
        console.error("Error loading chat history", err);
      });
  }
};

// Export for use by other modules
window.Chat = Chat;
