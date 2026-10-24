import { useState, useEffect, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { sendMessageToGateway } from "../api/chatApi";
import { showToast } from "../utils/toastNotifications";
import { useTelemetry } from "../context/metrics";

export const useChatEngine = () => {
  const { recordRequest } = useTelemetry();
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState("Analyzing request...");
  const [isReconnecting, setIsReconnecting] = useState(false);

  const abortControllerRef = useRef(null);
  
  // Holds the session ID in volatile React memory. 
  // It is destroyed completely if the user hits F5 (Refresh).
  const sessionIdRef = useRef(null);

  // The obsolete useEffect that fired POST /clear on mount has been permanently removed.

  // Cycles through placeholder statuses while waiting for first network chunk
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

  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsTyping(false);
    setIsReconnecting(false);
  };

  const executePrompt = async (uiMessages, editIndex = null) => {
    // Generate a secure UUID if this is the very first message of the session
    if (!sessionIdRef.current) {
      sessionIdRef.current = uuidv4();
    }

    // Construct the lightweight payload containing ONLY the target message and the UUID
    const networkPayload = {
      messages: [uiMessages[uiMessages.length - 1]],
      session_id: sessionIdRef.current,
    };

    // Attach the truncation index if this is an edit or regeneration
    if (editIndex !== null) {
      networkPayload.edit_index = editIndex;
    }

    setMessages([...uiMessages, { role: "assistant", content: "" }]);
    setIsTyping(true);
    setIsReconnecting(false);

    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();

    let streamBuffer = "";
    let lastRenderTime = Date.now();

    try {
      await sendMessageToGateway(
        networkPayload,
        (chunk) => {
          setIsReconnecting(false);
          streamBuffer += chunk;
          const now = Date.now();
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
        (telemetry) => {
          recordRequest(telemetry);
        },
        (errorMessage) => {
          setIsReconnecting(false);
          showToast(errorMessage, "error");
          if (streamBuffer === "") setMessages((prev) => prev.slice(0, -1));
        },
        () => setIsReconnecting(true),
        abortControllerRef.current.signal,
      );
    } catch (err) {
      setIsReconnecting(false);
      showToast(err.message, "error");
      if (streamBuffer === "") setMessages((prev) => prev.slice(0, -1));
    } finally {
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

  return {
    messages,
    setMessages,
    isTyping,
    loadingStatus,
    isReconnecting,
    executePrompt,
    handleStopGenerating,
  };
};