import { useState, useRef, useEffect } from 'react';

interface InputBarProps {
  onSend: (text: string) => void;
  disabled: boolean;
}

export const InputBar = ({ onSend, disabled }: InputBarProps) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  const submit = () => {
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit();
  };

  return (
    <form className="p-4 border-t border-gray-200 flex gap-2 items-end" onSubmit={handleSubmit}>
      <textarea
        ref={textareaRef}
        rows={2}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={disabled ? 'Sending...' : 'Type your message...'}
        disabled={disabled}
        className="flex-1 py-2 px-4 border border-gray-300 rounded-2xl text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors resize-none overflow-y-hidden leading-5"
      />
      <button
        type="submit"
        disabled={disabled || !input.trim()}
        className="py-2 px-5 bg-blue-600 text-white border-0 rounded-full text-sm font-semibold cursor-pointer hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shrink-0"
      >
        Send
      </button>
    </form>
  );
};
