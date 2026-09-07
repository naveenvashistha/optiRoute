import React, { useState, useRef } from "react";
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
    isBackendDirty,
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
    isBackendDirty.current = true;
    executePrompt(uiMessages);
  };

  const handleRegenerate = (index) => {
    if (isTyping) return;
    const uiMessages = messages.slice(0, index);
    isBackendDirty.current = true;
    executePrompt(uiMessages);
  };

  const handleCopyMessage = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgIndex(index);
    if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    copyTimeoutRef.current = setTimeout(() => setCopiedMsgIndex(null), 2000);
  };

  return (
    <div className="chat-container" style={{ position: "relative" }}>
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
      >
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
