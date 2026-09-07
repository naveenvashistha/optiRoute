/**
 * Chat API Client Module
 * ======================
 * Handles all network communications between the React frontend and the FastAPI backend.
 * Features native stream processing for Server-Sent Events (SSE), exponential backoff 
 * for network resilience, and AbortController integration for canceling requests mid-flight.
 */

const API_BASE_URL = "http://localhost:8000/api";

/**
 * Utility: Pauses execution for a specified duration.
 * Used exclusively by the exponential backoff algorithm during network retries.
 * 
 * @param {number} ms - The number of milliseconds to wait.
 * @returns {Promise<void>}
 */
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Sends the conversation history to the Smart Gateway and processes the SSE stream.
 * 
 * @param {Array<Object>} messages - The payload sent to the server (e.g., [{role: 'user', content: '...'}]).
 * @param {function(string): void} onChunk - Callback fired when a new text token arrives.
 * @param {function(Object): void} onTelemetry - Callback fired when the final routing metrics arrive.
 * @param {function(string): void} onError - Callback fired on fatal HTTP errors or mid-stream backend crashes.
 * @param {function(): void} onRetry - Callback fired when a connection drops and the client attempts to reconnect.
 * @param {AbortSignal} abortSignal - The DOM signal used to instantly sever the fetch request if the user clicks "Stop Generating".
 * @param {number} [maxRetries=3] - Maximum number of connection attempts before permanently failing.
 */
export const sendMessageToGateway = async (
  messages,
  onChunk,
  onTelemetry,
  onError,
  onRetry,
  abortSignal,
  maxRetries = 3,
) => {
  let attempt = 0;
  let delay = 1000;

  while (attempt < maxRetries) {
    try {
      // 1. Initialize the HTTP POST Request
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages }),
        signal: abortSignal, // Attach the abort signal to the network request
      });

      // 2. Handle HTTP Errors (e.g., 400 Bad Request, 429 Rate Limit, 500 Server Error)
      if (!response.ok) {
        if (response.status >= 400 && response.status < 500) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.detail || `Client Error: ${response.status}`,
          );
        }
        throw new Error(`Server Error: ${response.status}`);
      }

      // 3. Attach the Stream Reader
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // 4. Process the Server-Sent Events (SSE) Stream
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        // Decode the raw bytes into text and append to our buffer
        buffer += decoder.decode(value, { stream: true });
        
        // Split the buffer by newlines. The last element might be an incomplete chunk,
        // so we pop it off and leave it in the buffer for the next network cycle.
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              // Parse the JSON payload sent by the FastAPI event_generator()
              const data = JSON.parse(line.slice(6));

              // Intercept internal backend failures (e.g., SLM model crashed mid-sentence)
              if (data.error) {
                onError(`[Gateway Error]: ${data.error}`);
                return; // Immediately halt frontend stream processing
              }

              // Standard text generation token
              if (data.chunk) {
                onChunk(data.chunk);
              }
              
              // Performance and routing metrics (arrives at the very end of the stream)
              if (data.telemetry) {
                onTelemetry(data.telemetry);
              }
            } catch (e) {
              // Silently ignore JSON parse errors. This is expected behavior if an SSE chunk 
              // splits a JSON object perfectly in half across two TCP packets. It will be 
              // caught and completed in the next reader cycle.
            }
          }
        }
      }
      
      // If we break out of the while loop naturally, the stream completed successfully.
      return; 

    } catch (error) {
      // --- ERROR HANDLING & RETRY LOGIC ---

      // 1. Silent Exit: If the user manually clicked the "Stop Generating" button,
      // it throws an 'AbortError'. We catch it and exit cleanly without showing a Toast.
      if (error.name === "AbortError") {
        console.log("Stream aborted by user.");
        return;
      }

      attempt++;
      console.warn(
        `Gateway connection failed (Attempt ${attempt}/${maxRetries}): ${error.message}`,
      );

      // 2. Fatal Errors: Do not retry if the server explicitly rejected the request (4xx Client Error),
      // or if we have exhausted all our retry attempts.
      if (attempt >= maxRetries || error.message.includes("Client Error")) {
        onError(error.message);
        return;
      }

      // 3. Retry Sequence: Notify the UI to show the "Reconnecting..." overlay
      if (onRetry) onRetry();

      // Exponential Backoff: Wait 1s, then 2s, then 4s, to give the server time to recover
      await sleep(delay);
      delay *= 2;
    }
  }
};