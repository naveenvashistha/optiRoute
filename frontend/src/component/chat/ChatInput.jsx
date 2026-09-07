import React, { useRef } from "react";

const ChatInput = ({ input, setInput, isTyping, handleSend, handleStopGenerating }) => {
  const textareaRef = useRef(null);

  const handleInput = (e) => {
    setInput(e.target.value);
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
      textarea.style.overflowY = textarea.scrollHeight > 200 ? "auto" : "hidden";
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
        textareaRef.current.style.overflowY = "hidden";
      }
    }
  };

  const submitClick = () => {
    handleSend();
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.overflowY = "hidden";
    }
  };

  return (
    <div className="chat-input-area">
      <div className="input-box-wrapper">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question or enter code..."
          rows="1"
          style={{ overflowY: "hidden" }}
        />
        {isTyping ? (
          <button onClick={handleStopGenerating} className="icon-action-btn stop-btn" title="Stop Generating">
            <svg width="20" height="20" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2" ry="2" /></svg>
          </button>
        ) : (
          <button onClick={submitClick} disabled={!input.trim()} className="icon-action-btn" title="Send Message">
            <svg width="20" height="20" fill="currentColor" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" /></svg>
          </button>
        )}
      </div>
    </div>
  );
};

export default ChatInput;