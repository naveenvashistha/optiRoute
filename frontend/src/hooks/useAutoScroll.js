import { useState, useRef, useEffect } from "react";

export const useAutoScroll = (dependencies) => {
  const [showScrollButton, setShowScrollButton] = useState(false);
  const chatHistoryRef = useRef(null);
  const autoScrollEnabled = useRef(true);

  // Auto-scrolls the container whenever dependencies update, ONLY IF user hasn't scrolled up manually
  useEffect(() => {
    if (chatHistoryRef.current && autoScrollEnabled.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, dependencies);

  // Calculates scrollbar math to determine if the Auto-Scroll Anchor should be detached
  const handleScroll = () => {
    if (!chatHistoryRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatHistoryRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    autoScrollEnabled.current = isAtBottom;
    setShowScrollButton(!isAtBottom);
  };

  // Forces the scrollbar to the bottom and re-engages the anchor
  const scrollToBottom = () => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
      autoScrollEnabled.current = true;
      setShowScrollButton(false);
    }
  };

  return { chatHistoryRef, showScrollButton, handleScroll, scrollToBottom };
};