import toast from "react-hot-toast";

/**
 * Intercepts raw technical errors and renders a human-friendly custom UI toast.
 */
export const showToast = (rawError, type = "error") => {
  let title = "Oops!";
  let message = "Something went wrong on our end. Please give it another try.";
  const errStr = String(rawError).toLowerCase();

  if (errStr.includes("connection") || errStr.includes("network") || errStr.includes("failed to fetch")) {
    title = "Connection Lost";
    message = "Please check your internet connection and try again.";
  } else if (errStr.includes("429") || errStr.includes("rate limit")) {
    title = "Slow Down";
    message = "You're sending messages a bit too fast. Please wait a moment.";
  } else if (errStr.includes("timeout") || errStr.includes("interrupted")) {
    title = "Request Timed Out";
    message = "The response took too long. Please try a simpler prompt.";
  } else if (errStr.includes("400") || errStr.includes("payload")) {
    title = "Invalid Request";
    message = "We couldn't process that message. Please try rephrasing.";
  } else if (errStr.includes("500") || errStr.includes("503") || errStr.includes("gateway")) {
    title = "Server Hiccup";
    message = "Our servers are currently experiencing issues. We're on it!";
  }

  toast.custom(
    (t) => (
      <div className={`optiroute-toast ${type}`}>
        <div className="toast-icon-container">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
          </svg>
        </div>
        <div className="toast-text-content">
          <span className="toast-title">{title}</span>
          <span className="toast-message">{message}</span>
        </div>
        <button className="toast-close-btn" onClick={() => toast.dismiss(t.id)}>
          X
        </button>
      </div>
    ),
    { duration: 5000 }
  );
};