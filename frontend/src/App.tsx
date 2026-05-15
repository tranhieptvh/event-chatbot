import { useState, useCallback } from 'react';
import { ChatWidget } from './components/ChatWidget';
import { EventList } from './components/EventList';
import './styles/chat.css';

function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const handleEventCreated = useCallback(() => setRefreshKey(k => k + 1), []);

  return (
    <div className="min-h-screen bg-gray-100">
      <EventList refreshKey={refreshKey} />
      <ChatWidget onEventCreated={handleEventCreated} />
    </div>
  );
}

export default App;
