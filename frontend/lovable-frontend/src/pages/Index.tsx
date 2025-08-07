import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PanelLeft, PanelLeftClose } from "lucide-react";
import { AdminSidebar } from "@/components/AdminSidebar";
import { ChatInterface } from "@/components/ChatInterface";
import { ChatMessage } from "@/services/api";

const Index = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <AdminSidebar isOpen={sidebarOpen} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Sidebar Toggle */}
        <div className="p-3 border-b border-gray-100 bg-white/80 backdrop-blur-sm">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            {sidebarOpen ? (
              <>
                <PanelLeftClose className="w-4 h-4" />
                Hide Admin Panel
              </>
            ) : (
              <>
                <PanelLeft className="w-4 h-4" />
                Show Admin Panel
              </>
            )}
          </Button>
        </div>

        {/* Chat Interface */}
        <ChatInterface
          messages={messages}
          onMessagesUpdate={setMessages}
        />
      </div>
    </div>
  );
};

export default Index;
