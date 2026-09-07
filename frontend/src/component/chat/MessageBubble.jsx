import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeRaw from "rehype-raw";
import rehypeKatex from "rehype-katex";
import CodeBlock from "./CodeBlock";
import { preprocessLaTeX } from "../../utils/markdownUtils";

const MessageBubble = ({
  msg,
  index,
  isTyping,
  editingIndex,
  setEditingIndex,
  editDraft,
  setEditDraft,
  submitInlineEdit,
  handleCopyMessage,
  copiedMsgIndex,
  handleRegenerate,
}) => {
  return (
    <div className={`message-wrapper ${msg.role === "user" ? "user-wrapper" : "ai-wrapper"}`}>
      {msg.role === "user" ? (
        <div className="message-inner-container user-inner">
          {editingIndex === index ? (
            <div className="inline-edit-container">
              <textarea
                className="inline-edit-textarea"
                value={editDraft}
                onChange={(e) => setEditDraft(e.target.value)}
                rows={Math.max(1, editDraft.split("\n").length)}
                autoFocus
              />
              <div className="inline-edit-actions">
                <button className="inline-edit-btn" onClick={() => setEditingIndex(null)}>Cancel</button>
                <button className="inline-edit-btn submit" onClick={() => submitInlineEdit(index)}>Submit</button>
              </div>
            </div>
          ) : (
            <>
              <div className="user-bubble">{msg.content}</div>
              <div className="message-action-row">
                <button className="action-btn" title="Copy Prompt" onClick={() => handleCopyMessage(msg.content, index)} disabled={isTyping}>
                  {copiedMsgIndex === index ? (
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  ) : (
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="8" width="12" height="12" rx="2" ry="2" /><path d="M8 8V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2" /></svg>
                  )}
                </button>
                <button className="action-btn" title="Edit Prompt" onClick={() => setEditingIndex(index)} disabled={isTyping}>
                  <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                </button>
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="message-inner-container">
          <div className="ai-content-canvas">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeRaw, [rehypeKatex, { throwOnError: false, errorColor: "#f43f5e", macros: { "\\slashed": "\\not{#1}" } }]]}
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || "");
                  const codeString = String(children).replace(/\n$/, "");
                  return !inline && match ? (
                    <CodeBlock language={match[1]} value={codeString} />
                  ) : (
                    <code className="inline-code" {...props}>{children}</code>
                  );
                },
              }}
            >
              {preprocessLaTeX(msg.content)}
            </ReactMarkdown>
          </div>
          {msg.content !== "" && (
            <div className="message-action-row">
              <button className="action-btn" title="Copy Response" onClick={() => handleCopyMessage(msg.content, index)} disabled={isTyping}>
                {copiedMsgIndex === index ? (
                  <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                ) : (
                  <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="8" width="12" height="12" rx="2" ry="2" /><path d="M8 8V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2" /></svg>
                )}
              </button>
              <button className="action-btn" title="Regenerate Response" onClick={() => handleRegenerate(index)} disabled={isTyping}>
                <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MessageBubble;