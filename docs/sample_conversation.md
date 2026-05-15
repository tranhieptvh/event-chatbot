# Sample Conversation

The bot asks for required fields in the order defined by `FIELD_PRIORITY` in [backend/app/services/conversation.py](../backend/app/services/conversation.py):
`name → date → time → description → venue_name → venue_address → capacity → organizer_name → organizer_email → ticket_limit → purchase_start → purchase_end → is_recurring → (recurrence_frequency if recurring) → category → language → is_online → seat_types`.

All 17 fields are required per the spec. `recurrence_frequency` is only asked when `is_recurring=true`.

---

## Successful event creation

```
User:  I want to organize a jazz concert called "Kyoto Jazz Night" on March 10, 2027.
AI:    Got it — "Kyoto Jazz Night" on 2027-03-10. What time does it start? (HH:MM, 24-hour)

User:  7pm.
AI:    Noted, 19:00. Can you give a brief description of the event?

User:  A live jazz performance in Kyoto featuring local and international artists.
AI:    What's the name of the venue?

User:  Kyoto Concert Hall.
AI:    What's the venue address?

User:  123 Sakyo-ku, Kyoto.
AI:    What is the total venue capacity (total seats)?

User:  1000.
AI:    Who is the organizer?

User:  Fenix Entertainment.
AI:    What's the organizer's email address?

User:  info@fenix.co.jp
AI:    How many tickets can one person buy?

User:  4.
AI:    When should ticket sales start? (YYYY-MM-DD)

User:  2027-01-01.
AI:    When should ticket sales end? (YYYY-MM-DD)

User:  2027-03-09.
AI:    Is this a recurring event? (yes/no)

User:  No.
AI:    What category does this event belong to? (e.g., Concert, Conference)

User:  Concert.
AI:    What language will the event be conducted in?

User:  Japanese.
AI:    Is this an online event? (yes/no)

User:  No.
AI:    What types of seats are available and their prices? (e.g., VIP: 100000, Regular: 50000)

User:  VIP at 10,000 yen and Regular at 5,000 yen.
AI:    Here's a summary of your event:
       - Name: Kyoto Jazz Night
       - Date/Time: 2027-03-10 at 19:00
       - Description: A live jazz performance in Kyoto featuring local and international artists.
       - Venue: Kyoto Concert Hall, 123 Sakyo-ku, Kyoto (capacity 1000)
       - Tickets: VIP ¥10,000 / Regular ¥5,000 (limit 4/person)
       - On sale: 2027-01-01 → 2027-03-09
       - Organizer: Fenix Entertainment (info@fenix.co.jp)
       - Category: Concert · Language: Japanese · Online: no · Recurring: no
       Shall I save this event?

User:  Yes, save it.
AI:    Event "Kyoto Jazz Night" has been registered successfully!
```

---

## Handling invalid input

### Invalid email format

```
User:  hello@not
AI:    Thanks for the input. The organizer email you provided isn't valid:
       value is not a valid email address: The part after the @-sign is not
       valid. It should have a period. What's the organizer's email address?
```

### Invalid date relationship (sale end ≥ event date)

```
User:  2027-11-01                 (after providing event date 2027-10-15)
AI:    Thanks for the info. The ticket sale end date must be before the
       event date (2027-10-15). Could you provide a valid end date in
       YYYY-MM-DD format?
```
