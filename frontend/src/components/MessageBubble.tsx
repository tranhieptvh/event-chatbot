import type { Message } from '../types';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble = ({ message }: MessageBubbleProps) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex flex-col max-w-[80%] ${isUser ? 'self-end' : 'self-start'}`}>
      <div
        className={`py-2 px-3 rounded-2xl break-words whitespace-pre-wrap text-sm leading-relaxed ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : 'bg-gray-100 text-gray-800 rounded-bl-sm'
        }`}
      >
        {message.content}
      </div>
      {message.scenario && (
        <span className="text-[11px] text-gray-400 mt-1 px-1">{message.scenario}</span>
      )}
    </div>
  );
};
