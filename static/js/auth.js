// Authentication Module
const Auth = {
  elements: {},

  init() {
    this.elements = {
      loginContainer: document.getElementById("loginContainer"),
      chatContainer: document.getElementById("chatContainer"),
      loginForm: document.getElementById("loginForm"),
      passwordInput: document.getElementById("passwordInput"),
      loginError: document.getElementById("loginError"),
      envSelect: document.getElementById("envSelect")
    };

    this.attachEventListeners();
    this.checkAuth();
  },

  checkAuth() {
    const isAuthenticated = sessionStorage.getItem("authenticated");
    if (isAuthenticated === "true") {
      this.showChat();
    }
  },

  showChat() {
    this.elements.loginContainer.style.display = "none";
    this.elements.chatContainer.style.display = "flex";

    // Initialize chat after showing
    if (window.Chat && typeof window.Chat.init === "function") {
      window.Chat.init();
    }
  },

  attachEventListeners() {
    this.elements.loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const password = this.elements.passwordInput.value.trim();
      const baseUrl = this.elements.envSelect.value;

      try {
        const res = await fetch(`${baseUrl}/interface/verify-password`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password })
        });

        if (res.ok) {
          sessionStorage.setItem("authenticated", "true");
          this.showChat();
        } else {
          this.elements.loginError.textContent = "Invalid password";
          this.elements.loginError.style.display = "block";
          this.elements.passwordInput.value = "";
        }
      } catch (err) {
        this.elements.loginError.textContent = "Error connecting to server";
        this.elements.loginError.style.display = "block";
      }
    });
  }
};

// Initialize on DOM load
window.addEventListener("DOMContentLoaded", () => Auth.init());
