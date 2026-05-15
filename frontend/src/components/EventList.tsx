import { useEffect, useState } from 'react';
import { eventsAPI } from '../services/api';
import type { Event } from '../types';

interface EventListProps {
  refreshKey?: number;
}

export const EventList = ({ refreshKey }: EventListProps) => {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    eventsAPI.list()
      .then(setEvents)
      .catch(() => setError('Failed to load events'))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-8">
        <p className="text-center text-gray-400 py-12">Loading events...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-8">
        <p className="text-center text-red-400 py-12">{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 pb-28">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Upcoming Events</h2>

      {events.length === 0 ? (
        <p className="text-center text-gray-400 py-12 text-sm">
          No events yet. Use the chatbot to create one!
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {events.map(event => (
            <div
              key={event.id}
              className="bg-white rounded-xl p-5 shadow-sm flex flex-col gap-3 hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start gap-2">
                <h3 className="text-base font-semibold text-gray-900 leading-snug">
                  {event.name}
                </h3>
                <div className="flex flex-col gap-1 items-end">
                  {event.is_recurring && (
                    <span className="shrink-0 bg-blue-50 text-blue-600 text-[11px] font-semibold px-2 py-0.5 rounded-full uppercase">
                      {event.recurrence_frequency ?? 'Recurring'}
                    </span>
                  )}
                  {event.is_online && (
                    <span className="shrink-0 bg-emerald-50 text-emerald-600 text-[11px] font-semibold px-2 py-0.5 rounded-full uppercase">
                      Online
                    </span>
                  )}
                  {event.category && (
                    <span className="shrink-0 bg-purple-50 text-purple-600 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                      {event.category}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-1 text-xs text-gray-500">
                <span>📅 {event.date} {event.time}</span>
                <span>📍 {event.venue_name}</span>
                <span className="ml-4 text-[11px]">{event.venue_address}</span>
                <span>🎟️ {event.ticket_limit.toLocaleString()} tickets / person · capacity {event.capacity.toLocaleString()}</span>
              </div>

              {event.description && (
                <p className="text-xs text-gray-600 leading-relaxed">{event.description}</p>
              )}

              {Object.keys(event.seat_types).length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(event.seat_types).map(([name, price]) => (
                    <span
                      key={name}
                      className="bg-gray-100 text-gray-600 text-[11px] px-2 py-0.5 rounded"
                    >
                      {name}: {Number(price).toLocaleString()}
                    </span>
                  ))}
                </div>
              )}

              <div className="flex flex-col gap-0.5 text-[11px] text-gray-400 mt-auto pt-2 border-t border-gray-100">
                <span>Sale: {event.purchase_start} → {event.purchase_end}</span>
                <span>Organizer: {event.organizer_name} · {event.organizer_email}</span>
                {event.language && <span>Language: {event.language}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
