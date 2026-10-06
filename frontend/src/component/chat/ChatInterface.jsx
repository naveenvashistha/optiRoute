import React, { useState, useRef, useEffect } from "react";
import { Toaster } from "react-hot-toast";
import { useChatEngine } from "../../hooks/useChatEngine";
import { useAutoScroll } from "../../hooks/useAutoScroll";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import "./chat.css";

const ChatInterface = () => {
  const {
    messages,
    isTyping,
    loadingStatus,
    isReconnecting,
    executePrompt,
    handleStopGenerating,
  } = useChatEngine();

  const { chatHistoryRef, showScrollButton, handleScroll, scrollToBottom } =
    useAutoScroll([messages, isTyping, loadingStatus]);

  const [input, setInput] = useState("");
  const [editingIndex, setEditingIndex] = useState(null);
  const [editDraft, setEditDraft] = useState("");
  const [copiedMsgIndex, setCopiedMsgIndex] = useState(null);
  const copyTimeoutRef = useRef(null);

  // --- ANIMATION STATES ---
  const hasMessages = messages.length > 0;
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [hideGreeting, setHideGreeting] = useState(hasMessages);

  // Trigger the Fade & Rise animation when the first message is sent
  useEffect(() => {
    if (hasMessages && !hideGreeting) {
      setIsFadingOut(true);
      // Wait for the 700ms CSS transition to finish before unmounting the component
      const timer = setTimeout(() => setHideGreeting(true), 700);
      return () => clearTimeout(timer);
    }
  }, [hasMessages, hideGreeting]);

  const handleSend = () => {
    if (!input.trim() || isTyping) return;
    const uiMessages = [...messages, { role: "user", content: input.trim() }];
    setInput("");
    executePrompt(uiMessages);
  };

  const submitInlineEdit = (index) => {
    if (!editDraft.trim() || isTyping) return;
    const uiMessages = messages.slice(0, index);
    uiMessages.push({ role: "user", content: editDraft.trim() });
    setEditingIndex(null);
    executePrompt(uiMessages, index);
  };

  const handleRegenerate = (index) => {
    if (isTyping) return;
    const uiMessages = messages.slice(0, index);
    executePrompt(uiMessages, index - 1);
  };

  const handleCopyMessage = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgIndex(index);
    if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    copyTimeoutRef.current = setTimeout(() => setCopiedMsgIndex(null), 2000);
  };

  return (
    <div
      className="chat-container"
      style={{
        position: "relative",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* <Toaster
        position="top-right"
        containerStyle={{
          top: "4.5rem",
          right: "0.75rem",
          zIndex: 9999,
        }}
      /> */}

      {isReconnecting && (
        <div className="reconnecting-overlay">
          No internet • Reconnecting...
        </div>
      )}

      {showScrollButton && (
        <button
          className="scroll-to-bottom-btn"
          onClick={scrollToBottom}
          title="Scroll to bottom"
        >
          <svg
            width="20"
            height="20"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </button>
      )}

      <div
        className="chat-history"
        ref={chatHistoryRef}
        onScroll={handleScroll}
        style={{ flexGrow: 1, overflowY: "auto", position: "relative" }}
      >
        {/* Render a Centered Splash Screen with Blur-Fade & Rise Animation */}
        {!hideGreeting && (
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              // 1. Shift up AND scale down slightly to push it "into the background"
              transform: isFadingOut
                ? "translate(-50%, -60%) scale(0.95)"
                : "translate(-50%, -50%) scale(1)",
              // 2. Drop opacity to make it transparent
              opacity: isFadingOut ? 0 : 1,
              // 3. Apply the blur filter so the text "evaporates"
              filter: isFadingOut ? "blur(1px)" : "blur(0px)",
              // 4. Smooth 700ms transition for all properties simultaneously
              transition: "all 1.2s cubic-bezier(0.4, 0, 0.2, 1)",
              textAlign: "center",
              maxWidth: "650px",
              width: "100%",
              padding: "0 20px",
              pointerEvents: isFadingOut ? "none" : "auto",
            }}
          >
            <h2
              style={{
                color: "#facc15",
                fontSize: "1.5rem",
                fontWeight: "600",
                marginBottom: "1.5rem",
              }}
            >
              Welcome to the OptiRoute Gateway.
            </h2>
            <p
              style={{
                color: "#a1a1aa",
                fontSize: "1.125rem",
                lineHeight: "1.75",
                marginBottom: "2rem",
              }}
            >
              I intelligently analyze your prompts to find the perfect balance
              of speed and power-routing everyday questions to lightning-fast
              free models, and reserving premium cloud compute for heavy
              analytics.
            </p>
            <p
              style={{ color: "#52525b", fontSize: "1rem", fontWeight: "500" }}
            >
              Let's see what we can solve today.
            </p>
          </div>
        )}

        {/* The dynamic message map (Index 0 is now guaranteed to be the user's first message) */}
        {messages.map((msg, index) => (
          <MessageBubble
            key={index}
            msg={msg}
            index={index}
            isTyping={isTyping}
            editingIndex={editingIndex}
            setEditingIndex={(idx) => {
              setEditingIndex(idx);
              setEditDraft(messages[idx].content);
            }}
            editDraft={editDraft}
            setEditDraft={setEditDraft}
            submitInlineEdit={submitInlineEdit}
            handleCopyMessage={handleCopyMessage}
            copiedMsgIndex={copiedMsgIndex}
            handleRegenerate={handleRegenerate}
          />
        ))}
        {isTyping && messages[messages.length - 1]?.content === "" && (
          <div className="message-wrapper ai-wrapper">
            <div className="loading-row">
              <span className="pulse-dot"></span>
              {loadingStatus}
            </div>
          </div>
        )}
      </div>

      <ChatInput
        input={input}
        setInput={setInput}
        isTyping={isTyping}
        handleSend={handleSend}
        handleStopGenerating={handleStopGenerating}
      />
    </div>
  );
};

export default ChatInterface;
