import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, MessageCircle, Terminal } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { TypingIndicator } from "./TypingIndicator";
import { apiService, ChatMessage as ChatMessageType } from "@/services/api";
import { toast } from "@/hooks/use-toast";

interface ChatInterfaceProps {
  messages: ChatMessageType[];
  onMessagesUpdate: (messages: ChatMessageType[]) => void;
}

export const ChatInterface = ({ messages, onMessagesUpdate }: ChatInterfaceProps) => {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const formatTimestamp = () => {
    return new Date().toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  };

  const handleSend = async () => {
  const question = input.trim();
  if (!question || isLoading) return;

  const userMessage: ChatMessageType = {
    role: "user",
    content: question,
    timestamp: formatTimestamp(),
  };

  const updatedMessages = [...messages, userMessage];
  onMessagesUpdate(updatedMessages);
  setInput("");
  setIsLoading(true);

  try {
    const response = await apiService.query(question);
    console.log("API response:", response);

    // Defensive formatting
    const answer = typeof response.answer === "string" ? response.answer : "⚠️ No answer received.";
    const sources = Array.isArray(response.sources)
      ? response.sources
      : typeof response.sources === "string"
      ? (response.sources as string).split("\n").filter(Boolean)
      : [];

    const metadata = typeof response.metadata_used === "string"
      ? response.metadata_used
      : response.metadata_used
      ? JSON.stringify(response.metadata_used, null, 2)
      : "No metadata";

    // Update logs from API response
    if (response.logs && Array.isArray(response.logs)) {
      setLogs(response.logs);
    }

    const assistantMessage: ChatMessageType = {
      role: "assistant",
      content: answer,
      sources,
      metadata,
      timestamp: formatTimestamp(),
    };

    onMessagesUpdate([...updatedMessages, assistantMessage]);
  } catch (error) {
    const errorMessage: ChatMessageType = {
      role: "assistant",
      content: "❌ Sorry, I encountered an error while processing your request. Please try again.",
      timestamp: formatTimestamp(),
    };

    onMessagesUpdate([...updatedMessages, errorMessage]);

    toast({
      title: "Error",
      description: error instanceof Error ? error.message : "Connection error",
      variant: "destructive",
    });
  } finally {
    setIsLoading(false);
    inputRef.current?.focus();
  }
};

  const handleClearChat = () => {
    onMessagesUpdate([]);
    toast({
      title: "Chat Cleared",
      description: "Chat history has been cleared",
    });
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-gray-100 p-4 text-center">
        <h1 className="text-lg font-medium text-gray-800 tracking-tight">RAG Assistant</h1>
        <p className="text-xs text-gray-500 mt-1">Ask questions about your documents</p>
      </div>

      {/* Main Content Area with Chat and Sidebar */}
      <div className="flex-1 flex min-h-0">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Messages Area */}
          <div className="flex-1 m-6 overflow-hidden flex flex-col">
            <div className="flex-1 overflow-y-auto space-y-6 px-2 custom-scrollbar max-h-[calc(100vh-200px)]">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center py-16">
                  <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-4">
                    <MessageCircle className="w-6 h-6 text-gray-400" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Welcome to RAG Chat
                  </h3>
                  <p className="text-gray-500 max-w-sm text-sm leading-relaxed">
                    Start a conversation by typing your question below. I can help you find information from your uploaded documents.
                  </p>
                </div>
              ) : (
                <>
                  {messages.map((message, index) => (
                    <ChatMessage key={index} message={message} />
                  ))}
                  {isLoading && <TypingIndicator />}
                </>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="border-t border-gray-100 bg-white/50 backdrop-blur-sm p-4">
              <div className="flex gap-3">
                <Input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="Ask me anything about your documents..."
                  disabled={isLoading}
                  className="flex-1 border-gray-200 focus:border-gray-300 focus:ring-1 focus:ring-gray-300 rounded-xl"
                />
                <Button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  size="icon"
                  className="shrink-0 rounded-xl bg-gray-900 hover:bg-gray-800 text-white"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Clear Chat Button */}
          {messages.length > 0 && (
            <div className="mx-6 mb-6">
              <Button
                onClick={handleClearChat}
                variant="outline"
                size="sm"
                className="w-full border-gray-200 text-gray-600 hover:bg-gray-50 rounded-xl"
              >
                Clear Chat History
              </Button>
            </div>
          )}
        </div>

        {/* Logs Sidebar */}
        <div className="w-80 border-l border-gray-200 bg-gray-50/50 flex flex-col">
          <div className="p-4 border-b border-gray-200 bg-white/80 backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-gray-600" />
              <h2 className="text-sm font-medium text-gray-800">Backend Logs</h2>
            </div>
            <p className="text-xs text-gray-500 mt-1">Real-time processing logs</p>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {logs.length === 0 ? (
              <div className="text-center py-8">
                <Terminal className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No logs yet</p>
                <p className="text-xs text-gray-400 mt-1">Logs will appear when you ask a question</p>
              </div>
            ) : (
              <div className="space-y-1">
                <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap bg-white rounded-lg p-3 border border-gray-200 max-h-96 overflow-y-auto">
                  {logs.join('\n')}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};