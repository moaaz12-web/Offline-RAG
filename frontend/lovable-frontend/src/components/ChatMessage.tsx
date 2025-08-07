import { ChatMessage as ChatMessageType } from "@/services/api";

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage = ({ message }: ChatMessageProps) => {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-6 animate-in slide-in-from-right-2 duration-300">
        <div className="bg-gray-900 text-white rounded-2xl rounded-br-md px-4 py-3 max-w-[80%] shadow-sm max-h-96 overflow-y-auto custom-scrollbar">
          <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
          <div className="text-xs mt-2 opacity-70 text-right">
            {message.timestamp}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-6 animate-in slide-in-from-left-2 duration-300">
      <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-md px-4 py-3 max-w-[80%] shadow-sm max-h-96 overflow-y-auto custom-scrollbar">
        <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-800">{message.content}</div>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div className="text-xs font-medium text-gray-600 mb-2 flex items-center gap-1">
              <span className="w-1 h-1 bg-blue-500 rounded-full"></span>
              Sources
            </div>
            <div className="text-xs text-gray-600 leading-relaxed">
              {message.sources.join(' ').replace(/\s+/g, ' ').trim()}
            </div>
          </div>
        )}

        {/* Metadata display */}
        {message.metadata && (
          <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div className="text-xs font-medium text-gray-600 mb-2 flex items-center gap-1">
              <span className="w-1 h-1 bg-green-500 rounded-full"></span>
              Metadata
            </div>
            <pre className="whitespace-pre-wrap break-words text-xs text-gray-600 font-mono leading-relaxed">
              {message.metadata}
            </pre>
          </div>
        )}

        <div className="text-xs mt-2 text-gray-400">
          {message.timestamp}
        </div>
      </div>
    </div>
  );
};
