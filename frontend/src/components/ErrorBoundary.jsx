import { Component } from "react";
import i18n from "../i18n";

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Unhandled render error:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "center",
          justifyContent: "center", minHeight: "60vh", padding: "2rem", textAlign: "center", gap: "12px",
        }}>
          <div style={{ fontSize: "40px" }}>⚠️</div>
          <h2 style={{ margin: 0 }}>{i18n.t("errorBoundary.title")}</h2>
          <p style={{ color: "var(--muted, #888)", maxWidth: "420px" }}>
            {i18n.t("errorBoundary.message")}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: "8px 20px", borderRadius: "8px", border: "none",
              background: "var(--primary, #22c55e)", color: "#000", fontWeight: 600, cursor: "pointer",
            }}
          >
            {i18n.t("errorBoundary.reload")}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
