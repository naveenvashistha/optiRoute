import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeRaw from "rehype-raw";
import rehypeKatex from "rehype-katex";
import toast, { Toaster } from "react-hot-toast";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { sendMessageToGateway } from "../../api/chatApi";
import "./chat.css";

/**
 * ==========================================
 * COMPONENT: CodeBlock
 * ==========================================
 * Intercepts Markdown code blocks to provide syntax highlighting and action buttons.
 * Used internally by ReactMarkdown via the `components` prop.
 */
const CodeBlock = ({ language, value }) => {
  // Local state to manage the inline tick mark animation for this specific block
  const [copied, setCopied] = useState(false);

  // Writes directly to the OS clipboard and triggers the 2-second checkmark
  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Creates a Blob in memory, forces an OS-level download prompt, and revokes the URL
  const handleDownload = () => {
    const blob = new Blob([value], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;

    // Map common languages to their proper file extensions
    const extMap = {
      python: "py",
      javascript: "js",
      js: "js",
      html: "html",
      css: "css",
      json: "json",
      java: "java",
      cpp: "cpp",
    };
    const ext = extMap[language?.toLowerCase()] || "txt";

    link.download = `snippet.${ext}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="code-block-wrapper">
      <div className="code-header">
        <span>{language || "text"}</span>
        <div className="header-actions">
          {/* Code Block Copy Button */}
          <button
            onClick={handleCopy}
            className="action-icon-btn"
            title="Copy code"
          >
            {copied ? (
              // The Checkmark SVG
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            ) : (
              // The Overlapping Rectangles Copy SVG
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="4" y="8" width="12" height="12" rx="2" ry="2" />
                <path d="M8 8V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2" />
              </svg>
            )}
          </button>
          {/* Code Block Download Button */}
          <button
            onClick={handleDownload}
            className="action-icon-btn"
            title="Download code"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>
        </div>
      </div>
      <SyntaxHighlighter
        language={language || "text"}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          padding: "1rem",
          fontSize: "0.88rem",
          background: "#09090b",
        }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
};

/**
 * ==========================================
 * UTILITY: preprocessLaTeX
 * ==========================================
 * Standardizes LaTeX delimiters before they reach the Markdown parser.
 * Uses negative lookbehinds (?<!\\) to safely ignore valid Matrix line breaks like \\[4pt]
 */
const preprocessLaTeX = (content) => {
  if (!content) return "";
  return content
    .replace(/(?<!\\)\\\[/g, "$$$")
    .replace(/(?<!\\)\\\]/g, "$$$")
    .replace(/(?<!\\)\\\(/g, "$")
    .replace(/(?<!\\)\\\)/g, "$");
};

/**
 * ==========================================
 * UTILITY: showToast
 * ==========================================
 * Intercepts raw technical errors from the API (like 429, 500, fetch failures)
 * and renders a human-friendly, color-coded custom UI toast.
 */
const showToast = (rawError, type = "error") => {
  let title = "Oops!";
  let message = "Something went wrong on our end. Please give it another try.";
  const errStr = String(rawError).toLowerCase();

  if (
    errStr.includes("connection") ||
    errStr.includes("network") ||
    errStr.includes("failed to fetch")
  ) {
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
  } else if (
    errStr.includes("500") ||
    errStr.includes("503") ||
    errStr.includes("gateway")
  ) {
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
    { duration: 5000 },
  );
};

/**
 * ==========================================
 * MAIN COMPONENT: ChatInterface
 * ==========================================
 */
const ChatInterface = () => {
  // ─── 1. CORE APPLICATION STATE ──────────────────────────────
  // Holds the active chat history. Initialized with a greeting.
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I am connected behind the **Smart API Gateway**.\n\nAsk me a general fact, a coding question, or to write something unique.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState("Analyzing request...");

  // ─── 2. UX INTERACTION STATE ────────────────────────────────
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [editingIndex, setEditingIndex] = useState(null); // Tracks which user message is currently being edited
  const [editDraft, setEditDraft] = useState(""); // Holds the draft text of the message being edited
  const [copiedMsgIndex, setCopiedMsgIndex] = useState(null); // Tracks which message copy button is currently showing a tick

  // ─── 3. MUTABLE DOM & NETWORK REFS ──────────────────────────
  const chatHistoryRef = useRef(null);
  const textareaRef = useRef(null);
  const autoScrollEnabled = useRef(true);
  const isBackendDirty = useRef(false); // Flags when the frontend array diverges from the backend memory
  const abortControllerRef = useRef(null); // Used to instantly sever HTTP streams
  const copyTimeoutRef = useRef(null); // Tracks the timeout for the inline copy tick mark

  // ─── 4. LIFECYCLE HOOKS ─────────────────────────────────────
  // Clears the backend process memory (Incognito Mode) whenever the tab is loaded or refreshed
  useEffect(() => {
    fetch("http://localhost:8000/api/clear", { method: "POST" }).catch(
      () => {},
    );
  }, []);

  // Cycles through placeholder statuses while waiting for the first network chunk to arrive
  useEffect(() => {
    if (!isTyping) return;
    const statuses = [
      "Analyzing request structure...",
      "Evaluating query complexity...",
      "Checking routing policy...",
      "Synthesizing response...",
    ];
    let i = 0;
    setLoadingStatus(statuses[0]);
    const interval = setInterval(() => {
      i = (i + 1) % statuses.length;
      setLoadingStatus(statuses[i]);
    }, 2400);
    return () => clearInterval(interval);
  }, [isTyping]);

  // Auto-scrolls the container whenever messages update, ONLY IF the user hasn't scrolled up manually
  useEffect(() => {
    if (chatHistoryRef.current && autoScrollEnabled.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages, isTyping, loadingStatus]);

  // ─── 5. UI EVENT HANDLERS ───────────────────────────────────
  // Dynamically adjusts textarea height based on user text volume
  const handleInput = (e) => {
    setInput(e.target.value);
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
      textarea.style.overflowY =
        textarea.scrollHeight > 200 ? "auto" : "hidden";
    }
  };

  // Calculates scrollbar math to determine if the Auto-Scroll Anchor should be attached or detached
  const handleScroll = () => {
    if (!chatHistoryRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatHistoryRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    autoScrollEnabled.current = isAtBottom;
    setShowScrollButton(!isAtBottom); // Show FAB if the user scrolled up
  };

  // Forces the scrollbar to the bottom and re-engages the anchor
  const scrollToBottom = () => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
      autoScrollEnabled.current = true;
      setShowScrollButton(false);
    }
  };

  // Writes to clipboard and triggers the inline tick mark specifically for message blocks
  const handleCopyMessage = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgIndex(index);
    if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    copyTimeoutRef.current = setTimeout(() => {
      setCopiedMsgIndex(null);
    }, 2000);
  };

  // Instantly halts the active connection via AbortController when "Stop Generating" is clicked
  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsTyping(false);
    setIsReconnecting(false);
  };

  // ─── 6. CORE EXECUTION PIPELINE ─────────────────────────────
  /**
   * Handles network payload routing, state synchronization, and SSE (Server-Sent Events) streaming.
   * Used as the master engine for standard sends, prompt edits, and AI regenerations.
   */
  const executePrompt = async (uiMessages) => {
    let networkPayload;

    // State Synchronization: If the user edited a past message, we clear the backend
    // and send the entire sliced array to re-sync the global memory.
    // Otherwise, we save bandwidth by only sending the newest text string.
    if (isBackendDirty.current) {
      await fetch("http://localhost:8000/api/clear", { method: "POST" }).catch(
        () => {},
      );
      networkPayload = uiMessages;
      isBackendDirty.current = false;
    } else {
      networkPayload = [uiMessages[uiMessages.length - 1]];
    }

    // Append the empty AI target bubble
    setMessages([...uiMessages, { role: "assistant", content: "" }]);
    setIsTyping(true);
    setIsReconnecting(false);

    // Reset the AbortController for the new request
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();

    let streamBuffer = "";
    let lastRenderTime = Date.now();

    try {
      await sendMessageToGateway(
        networkPayload,
        // Chunk Callback
        (chunk) => {
          setIsReconnecting(false);
          streamBuffer += chunk;
          const now = Date.now();
          // Rate-limit React state updates to 50ms to prevent render thrashing
          if (now - lastRenderTime > 50) {
            setMessages((prev) => {
              const lastIdx = prev.length - 1;
              return prev.map((msg, idx) =>
                idx === lastIdx ? { ...msg, content: streamBuffer } : msg,
              );
            });
            lastRenderTime = now;
          }
        },
        // Telemetry Callback
        (telemetry) => {
          console.log("Telemetry payload received:", telemetry);
        },
        // Error Callback
        (errorMessage) => {
          setIsReconnecting(false);
          showToast(errorMessage, "error");
          // Clean up the empty bubble if the request failed immediately
          if (streamBuffer === "") {
            setMessages((prev) => prev.slice(0, -1));
          }
        },
        // Retry Callback (Triggered when the network drops mid-stream)
        () => {
          setIsReconnecting(true);
        },
        // Pass the abort signal to the fetch API
        abortControllerRef.current.signal,
      );
    } catch (err) {
      setIsReconnecting(false);
      showToast(err.message, "error");
      if (streamBuffer === "") {
        setMessages((prev) => prev.slice(0, -1));
      }
    } finally {
      // Final Render Guarantee: Ensures the last few chunks are painted to the screen
      // if the stream ends rapidly between the 50ms render cycles.
      setMessages((prev) => {
        const lastIdx = prev.length - 1;
        if (prev[lastIdx]?.role === "assistant") {
          return prev.map((msg, idx) =>
            idx === lastIdx ? { ...msg, content: streamBuffer } : msg,
          );
        }
        return prev;
      });
      setIsTyping(false);
    }
  };

  // ─── 7. MESSAGE ROUTING HOOKS ───────────────────────────────
  // Submits a standard new message
  const handleSend = () => {
    if (!input.trim() || isTyping) return;
    const uiMessages = [...messages, { role: "user", content: input.trim() }];

    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.overflowY = "hidden";
    }
    executePrompt(uiMessages);
  };

  // Swaps a user message bubble into an inline editable textarea
  const handleEditClick = (index) => {
    if (isTyping) return;
    setEditingIndex(index);
    setEditDraft(messages[index].content);
  };

  // Slices the chat history and executes the modified prompt branch
  const submitInlineEdit = (index) => {
    if (!editDraft.trim() || isTyping) return;
    const uiMessages = messages.slice(0, index);
    uiMessages.push({ role: "user", content: editDraft.trim() });

    setEditingIndex(null);
    isBackendDirty.current = true; // Flags that we need to send the whole array
    executePrompt(uiMessages);
  };

  // Slices off the previous AI response and requests a new one with identical context
  const handleRegenerate = (index) => {
    if (isTyping) return;
    const uiMessages = messages.slice(0, index);
    isBackendDirty.current = true;
    executePrompt(uiMessages);
  };

  // Captures the Enter key to send messages, while allowing Shift+Enter for newlines
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ─── 8. JSX RENDER ──────────────────────────────────────────
  return (
    <div className="chat-container" style={{ position: "relative" }}>
      {/* Toast Notification Provider */}
      <Toaster position="top-right" />

      {/* Network Reconnection Overlay */}
      {isReconnecting && (
        <div className="reconnecting-overlay">
          No internet • Reconnecting...
        </div>
      )}

      {/* Floating Action Button (FAB) for auto-scrolling */}
      {showScrollButton && (
        <button
          className="scroll-to-bottom-btn"
          onClick={scrollToBottom}
          title="Scroll to bottom"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
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

      {/* Primary Chat Window */}
      <div
        className="chat-history"
        ref={chatHistoryRef}
        onScroll={handleScroll}
      >
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message-wrapper ${msg.role === "user" ? "user-wrapper" : "ai-wrapper"}`}
          >
            {/* ─── USER BUBBLE ─── */}
            {msg.role === "user" ? (
              <div className="message-inner-container user-inner">
                {editingIndex === index ? (
                  // Inline Edit Mode
                  <div className="inline-edit-container">
                    <textarea
                      className="inline-edit-textarea"
                      value={editDraft}
                      onChange={(e) => setEditDraft(e.target.value)}
                      rows={Math.max(1, editDraft.split("\n").length)}
                      autoFocus
                    />
                    <div className="inline-edit-actions">
                      <button
                        className="inline-edit-btn"
                        onClick={() => setEditingIndex(null)}
                      >
                        Cancel
                      </button>
                      <button
                        className="inline-edit-btn submit"
                        onClick={() => submitInlineEdit(index)}
                      >
                        Submit
                      </button>
                    </div>
                  </div>
                ) : (
                  // Standard Read Mode
                  <>
                    <div className="user-bubble">{msg.content}</div>
                    <div className="message-action-row">
                      {/* User Message Copy Button */}
                      <button
                        className="action-btn"
                        title="Copy Prompt"
                        onClick={() => handleCopyMessage(msg.content, index)}
                        disabled={isTyping}
                      >
                        {copiedMsgIndex === index ? (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polyline points="20 6 9 17 4 12"></polyline>
                          </svg>
                        ) : (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <rect
                              x="4"
                              y="8"
                              width="12"
                              height="12"
                              rx="2"
                              ry="2"
                            />
                            <path d="M8 8V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2" />
                          </svg>
                        )}
                      </button>
                      {/* User Message Edit Button */}
                      <button
                        className="action-btn"
                        title="Edit Prompt"
                        onClick={() => handleEditClick(index)}
                        disabled={isTyping}
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="16"
                          height="16"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                    </div>
                  </>
                )}
              </div>
            ) : (
              // ─── AI BUBBLE ───
              <div className="message-inner-container">
                <div className="ai-content-canvas">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[
                      rehypeRaw,
                      [
                        rehypeKatex,
                        {
                          throwOnError: false,
                          errorColor: "#f43f5e",
                          macros: { "\\slashed": "\\not{#1}" },
                        },
                      ],
                    ]}
                    components={{
                      // Injects our custom CodeBlock component whenever Markdown parses triple backticks
                      code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || "");
                        const codeString = String(children).replace(/\n$/, "");
                        return !inline && match ? (
                          <CodeBlock language={match[1]} value={codeString} />
                        ) : (
                          <code className="inline-code" {...props}>
                            {children}
                          </code>
                        );
                      },
                    }}
                  >
                    {preprocessLaTeX(msg.content)}
                  </ReactMarkdown>
                </div>
                {msg.content !== "" && (
                  <div className="message-action-row">
                    {/* AI Message Copy Button */}
                    <button
                      className="action-btn"
                      title="Copy Response"
                      onClick={() => handleCopyMessage(msg.content, index)}
                      disabled={isTyping}
                    >
                      {copiedMsgIndex === index ? (
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="16"
                          height="16"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                      ) : (
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="16"
                          height="16"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <rect
                            x="4"
                            y="8"
                            width="12"
                            height="12"
                            rx="2"
                            ry="2"
                          />
                          <path d="M8 8V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2" />
                        </svg>
                      )}
                    </button>
                    {/* AI Message Regenerate Button */}
                    <button
                      className="action-btn"
                      title="Regenerate Response"
                      onClick={() => handleRegenerate(index)}
                      disabled={isTyping}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="16"
                        height="16"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Loading Indicator for network latency before the first stream chunk arrives */}
        {isTyping && messages[messages.length - 1]?.content === "" && (
          <div className="message-wrapper ai-wrapper">
            <div className="loading-row">
              <span className="pulse-dot"></span>
              {loadingStatus}
            </div>
          </div>
        )}
      </div>

      {/* ─── CHAT INPUT AREA ─── */}
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
            // Active Stream: Stop Generating Button
            <button
              onClick={handleStopGenerating}
              className="icon-action-btn stop-btn"
              title="Stop Generating"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <rect x="6" y="6" width="12" height="12" rx="2" ry="2" />
              </svg>
            </button>
          ) : (
            // Idle State: Send Message Button
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="icon-action-btn"
              title="Send Message"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
