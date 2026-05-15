import { useState } from 'react';
import { MessageList } from './MessageList';
import { InputBar } from './InputBar';
import { useChat } from '../hooks/useChat';

interface ChatWidgetProps {
  onEventCreated?: () => void;
}

export const ChatWidget = ({ onEventCreated }: ChatWidgetProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const { messages, loading, sendMessage, clearChat } = useChat(onEventCreated);

  return (
    <>
      {!isOpen && (
        <button
          className="fixed bottom-5 right-5 w-14 h-14 rounded-full bg-blue-600 text-white text-2xl border-0 cursor-pointer shadow-lg hover:scale-110 transition-transform z-50"
          onClick={() => setIsOpen(true)}
        >
          💬
        </button>
      )}

      {isOpen && (
        <div className="fixed bottom-5 right-5 w-[380px] h-[600px] bg-white rounded-xl shadow-2xl flex flex-col z-50">
          <div className="px-4 py-3 bg-blue-600 text-white rounded-t-xl flex justify-between items-center">
            <h3 className="text-base font-semibold">Event Chatbot</h3>
            <div className="flex gap-1">
              <button
                onClick={clearChat}
                title="Clear chat"
                className="bg-transparent border-0 text-white text-lg cursor-pointer px-2 py-1 rounded hover:bg-white/20 transition-colors"
              >
                🗑️
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="bg-transparent border-0 text-white text-base font-bold cursor-pointer px-2 py-1 rounded hover:bg-white/20 transition-colors"
              >
                ✕
              </button>
            </div>
          </div>

          <MessageList messages={messages} />
          <InputBar onSend={sendMessage} disabled={loading} />
        </div>
      )}
    </>
  );
};
