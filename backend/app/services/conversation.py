"""Conversation service for managing chatbot interactions."""
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import EmailStr, TypeAdapter, ValidationError

_EMAIL_VALIDATOR = TypeAdapter(EmailStr)

from app.db.session import SessionLocal
from app.schemas.chat import ChatResponse, Scenario
from app.schemas.event import REQUIRED_FIELDS, EventCreate, EventDraft
from app.services import event_service, session_service, vector_store
from app.services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
with open(PROMPTS_DIR / "system_prompt.txt", "r") as f:
    SYSTEM_PROMPT = f.read()
with open(PROMPTS_DIR / "extraction_prompt.txt", "r") as f:
    EXTRACTION_PROMPT = f.read()


FIELD_PRIORITY = [
    "name", "date", "time", "description",
    "venue_name", "venue_address", "capacity",
    "organizer_name", "organizer_email",
    "ticket_limit", "purchase_start", "purchase_end",
    "is_recurring", "recurrence_frequency",
    "category", "language", "is_online",
    "seat_types",
]


FIELD_QUESTIONS = {
    "name": "What's the name of your event?",
    "date": "When is the event? (Please provide the date in YYYY-MM-DD format)",
    "time": "What time does it start? (Please use 24-hour HH:MM format)",
    "venue_name": "What's the name of the venue?",
    "venue_address": "What's the venue address?",
    "capacity": "What is the total venue capacity (total seats)?",
    "organizer_name": "Who is the organizer?",
    "organizer_email": "What's the organizer's email address?",
    "ticket_limit": "How many tickets can one person buy?",
    "purchase_start": "When should ticket sales start? (YYYY-MM-DD)",
    "purchase_end": "When should ticket sales end? (YYYY-MM-DD)",
    "is_recurring": "Is this a recurring event? (yes/no)",
    "recurrence_frequency": "How often does it repeat? (e.g., weekly, monthly, yearly)",
    "description": "Can you give a brief description of the event?",
    "category": "What category does this event belong to? (e.g., Concert, Conference)",
    "language": "What language will the event be conducted in? (e.g., English, Japanese)",
    "is_online": "Is this an online event? (yes/no)",
    "seat_types": (
        "What types of seats are available and their prices? "
        "(e.g., VIP: 100000, Regular: 50000)"
    ),
}


FIELD_DISPLAY_NAMES = {
    "name": "event name",
    "date": "event date",
    "time": "event time",
    "venue_name": "venue name",
    "venue_address": "venue address",
    "capacity": "venue capacity",
    "organizer_name": "organizer name",
    "organizer_email": "organizer email",
    "ticket_limit": "ticket limit per person",
    "purchase_start": "purchase start date",
    "purchase_end": "purchase end date",
    "is_recurring": "recurring",
    "recurrence_frequency": "recurrence frequency",
    "seat_types": "seat types and prices",
    "description": "description",
    "category": "category",
    "language": "language",
    "is_online": "online flag",
}


FIELD_LAST_ASKED_HINTS = {
    "name": ["name of your event", "event name"],
    "date": ["when is the event"],
    "time": ["what time", "24-hour", "hh:mm"],
    "venue_name": ["venue name", "name of the venue"],
    "venue_address": ["venue address"],
    "capacity": ["venue capacity", "total seats", "total venue"],
    "organizer_name": ["who is the organizer", "organizer name"],
    "organizer_email": ["organizer's email", "email address"],
    "ticket_limit": ["how many tickets", "tickets can one person", "ticket limit"],
    "purchase_start": ["sales start", "sale start", "purchase start"],
    "purchase_end": ["sales end", "sale end", "purchase end"],
    "is_recurring": ["recurring event", "does it repeat"],
    "recurrence_frequency": ["how often does it repeat", "frequency"],
    "description": ["brief description", "description of the event"],
    "category": ["category does this event", "category does this"],
    "language": ["language will the event"],
    "is_online": ["online event"],
    "seat_types": ["types of seats", "seat type", "seat types"],
}


CONFIRMATION_KEYWORDS = [
    "confirm", "correct", "looks good", "yes", "yeah", "yep", "ok", "okay",
    "save", "save it", "go ahead",
]


EDIT_KEYWORDS_PATTERN = re.compile(
    r"\b(change|update|edit|set|actually)\b",
    re.IGNORECASE,
)


DATE_FIELDS = {"date", "purchase_start", "purchase_end"}


class ConversationService:
    def __init__(self):
        self.llm = get_llm_provider()

    def process_message(self, session_id: str, user_message: str) -> ChatResponse:
        draft = session_service.get_draft(session_id) or {}
        history = session_service.get_history(session_id)

        session_service.append_history(session_id, "user", user_message)
        vector_store.add_message(session_id, "user", user_message)

        prior_draft = dict(draft)

        last_asked = self._get_last_asked_field(history)

        extracted = self._extract_fields(session_id, user_message, history, draft)

        # When the bot's last question was for purchase_start / purchase_end,
        # a bare date reply is often mis-tagged as `date` (event date) by the
        # LLM and the regex scanner. Re-route it to the field that was asked.
        if (
            last_asked in DATE_FIELDS
            and last_asked != "date"
            and extracted.get("date")
            and not extracted.get(last_asked)
        ):
            direct = self._direct_parse(user_message, last_asked)
            if direct and last_asked in direct:
                extracted[last_asked] = direct[last_asked]
                extracted.pop("date", None)

        for k, v in extracted.items():
            if v is None:
                continue
            if k in DATE_FIELDS and isinstance(v, str):
                normalized = self._parse_date_string(v)
                draft[k] = normalized if normalized else v
            else:
                draft[k] = v

        is_edit_intent = bool(EDIT_KEYWORDS_PATTERN.search(user_message))

        scanned = self._scan_message(user_message, last_asked=last_asked)
        for k, v in scanned.items():
            if draft.get(k) is None or k in extracted or is_edit_intent:
                draft[k] = v

        if last_asked and draft.get(last_asked) is None:
            direct = self._direct_parse(user_message, last_asked)
            if direct:
                draft.update(direct)

        session_service.set_draft(session_id, draft)

        is_edit = self._detect_edit(user_message, prior_draft, draft)

        response = self._determine_response(
            session_id, draft, user_message, history, is_edit=is_edit, prior_draft=prior_draft,
        )

        session_service.append_history(session_id, "assistant", response.message)
        vector_store.add_message(session_id, "assistant", response.message)

        return response

    def _extract_fields(
        self, session_id: str, user_message: str, history: list, draft: dict,
    ) -> Dict[str, Any]:
        recent = "\n".join([f"{m['role']}: {m['content']}" for m in history[-5:]])

        # When history is long, supplement the last 5 turns with the top-K
        # semantically relevant earlier turns from the vector store so the LLM
        # can still see context that scrolled past the sliding window.
        relevant_section = ""
        if len(history) > 5:
            relevant = vector_store.query_context(session_id, user_message, n_results=3)
            recent_contents = {m["content"] for m in history[-5:]}
            extra = [m for m in relevant if m["content"] not in recent_contents]
            if extra:
                relevant_section = (
                    "Relevant earlier context (semantic recall):\n"
                    + "\n".join(f"{m['role']}: {m['content']}" for m in extra)
                    + "\n\n"
                )

        prompt = (
            f"{EXTRACTION_PROMPT}\n\n"
            f"{relevant_section}"
            f"Conversation context:\n{recent}\n\n"
            f"Current draft:\n{json.dumps(draft)}\n\n"
            f"User message: {user_message}\n\n"
            f"Extracted fields (JSON only):"
        )

        try:
            text = self.llm.extract_fields(prompt).strip()
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in extraction response: %s", text[:200])
                return {}
            return json.loads(json_match.group())
        except Exception as e:
            logger.error("Field extraction failed: %s", e)
            return {}

    def _detect_edit(self, user_message: str, prior_draft: dict, draft: dict) -> Optional[str]:
        """Detect if user is editing an existing field. Returns field name or None."""
        if not EDIT_KEYWORDS_PATTERN.search(user_message):
            return None
        for field in FIELD_PRIORITY:
            prior_val = prior_draft.get(field)
            new_val = draft.get(field)
            if prior_val is not None and new_val is not None and prior_val != new_val:
                return field
        return None

    def _determine_response(
        self, session_id: str, draft: dict, user_message: str, history: list,
        is_edit: Optional[str] = None, prior_draft: Optional[dict] = None,
    ) -> ChatResponse:
        if self._is_confirmation(user_message, history):
            return self._handle_confirmation(session_id, draft)

        event_draft = EventDraft(**draft)

        try:
            non_null_draft = {k: v for k, v in draft.items() if v is not None}
            if all(f in non_null_draft for f in REQUIRED_FIELDS):
                EventCreate(**non_null_draft)
        except ValidationError as e:
            for error in e.errors():
                if error.get("type") == "missing":
                    continue
                field = error["loc"][0] if error["loc"] else "input"
                draft.pop(field, None)
                session_service.set_draft(session_id, draft)
                message = self._generate_error_message(field, error["msg"], draft)
                return ChatResponse(
                    session_id=session_id, role="assistant",
                    scenario=Scenario.INVALID_INPUT, message=message,
                )

        email_error = self._validate_email_early(draft, session_id)
        if email_error:
            return email_error

        date_error = self._validate_dates_early(draft, session_id)
        if date_error:
            return date_error

        if is_edit:
            new_val = draft.get(is_edit)
            display = FIELD_DISPLAY_NAMES.get(is_edit, is_edit)
            ack = f"Got it. Updated the {display} to {new_val!r}."
            if event_draft.is_complete():
                summary = self._generate_confirmation_message(draft, acknowledgement=ack)
                return ChatResponse(
                    session_id=session_id, role="assistant",
                    scenario=Scenario.UPDATE_PREVIOUS_FIELD, message=summary,
                )
            next_field = self._get_next_field(event_draft.missing_fields())
            question = FIELD_QUESTIONS.get(next_field, f"Please provide {next_field}.")
            message = f"{ack} Now, {question}"
            return ChatResponse(
                session_id=session_id, role="assistant",
                scenario=Scenario.UPDATE_PREVIOUS_FIELD, message=message,
            )

        if event_draft.is_complete():
            message = self._generate_confirmation_message(draft)
            return ChatResponse(
                session_id=session_id, role="assistant",
                scenario=Scenario.CONFIRMATION, message=message,
            )

        missing = event_draft.missing_fields()
        next_field = self._get_next_field(missing)
        message = self._generate_question(next_field, draft, prior_draft)
        return ChatResponse(
            session_id=session_id, role="assistant",
            scenario=Scenario.MISSING_FIELD, message=message,
        )

    def _is_confirmation(self, user_message: str, history: list) -> bool:
        if not history:
            return False
        last_assistant = next(
            (msg for msg in reversed(history) if msg["role"] == "assistant"), None
        )
        if not last_assistant:
            return False
        user_lower = user_message.lower().strip()
        if not any(kw in user_lower for kw in CONFIRMATION_KEYWORDS):
            return False
        if EDIT_KEYWORDS_PATTERN.search(user_message):
            return False
        return any(
            kw in last_assistant["content"].lower()
            for kw in ["confirm", "shall i save", "is this correct"]
        )

    def _handle_confirmation(self, session_id: str, draft: dict) -> ChatResponse:
        try:
            event_create = EventCreate(**draft)
            db = SessionLocal()
            try:
                event_id = event_service.insert(event_create, db)
            finally:
                db.close()
            message = (
                f"Event '{event_create.name}' saved successfully! "
                f"(Event ID: {event_id})"
            )
            return ChatResponse(
                session_id=session_id, role="assistant",
                scenario=Scenario.SUCCESS_SAVE, message=message,
            )
        except event_service.DuplicateEventError as e:
            message = (
                f"An event with the same name and date already exists. {e} "
                f"Please change the name or date to continue."
            )
            return ChatResponse(
                session_id=session_id, role="assistant",
                scenario=Scenario.ERROR_DB, message=message,
            )
        except ValidationError as e:
            invalid_fields = []
            for error in e.errors():
                loc = error.get("loc", [])
                field = loc[0] if loc else None
                if field and field in draft:
                    draft.pop(field, None)
                    invalid_fields.append(str(field))
            session_service.set_draft(session_id, draft)
            field_list = ", ".join(invalid_fields) if invalid_fields else "some fields"
            msg = e.errors()[0].get("msg", "Invalid value").replace("Value error, ", "")
            message = f"{msg}. Please provide correct values for: {field_list}."
            return ChatResponse(
                session_id=session_id, role="assistant",
                scenario=Scenario.INVALID_INPUT, message=message,
            )
        except Exception as e:
            logger.exception("DB save failed")
            message = f"Failed to save event due to a database error: {e}."
            return ChatResponse(
                session_id=session_id, role="assistant",
                scenario=Scenario.ERROR_DB, message=message,
            )

    def _scan_message(self, msg: str, last_asked: Optional[str] = None) -> dict:
        result = {}

        m = re.search(r'["“”‘’]([^"“”‘’]+)["“”‘’]', msg)
        if not m:
            m = re.search(
                r'(?:named?|called?)\s+["\']?([A-Za-z0-9][^,.\n]{1,60}?)["\']?(?:[,.\n]|$)',
                msg, re.IGNORECASE,
            )
        if m:
            result['name'] = m.group(1).strip()

        date_candidates = []
        for dm in re.finditer(
            r'\b(\d{4}-\d{2}-\d{2})\b'
            r'|\b(\d{1,2})/(\d{1,2})/(\d{4})\b',
            msg,
        ):
            g = dm.groups()
            if g[0]:
                date_candidates.append(g[0])
            elif g[1]:
                d, mo, y = g[1].zfill(2), g[2].zfill(2), g[3]
                date_candidates.append(f"{y}-{mo}-{d}")
        if date_candidates:
            target = last_asked if last_asked in DATE_FIELDS else 'date'
            result[target] = date_candidates[0]

        time_match = re.search(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', msg)
        if time_match:
            result['time'] = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"

        m = re.search(r'\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b', msg)
        if m:
            result['organizer_email'] = m.group()

        m = re.search(r'(\d+)\s*tickets?\b', msg, re.IGNORECASE)
        if m:
            result['ticket_limit'] = int(m.group(1))

        m = re.search(r'(\d+)\s*(?:seats?|capacity)\b', msg, re.IGNORECASE)
        if m:
            result['capacity'] = int(m.group(1))

        lower = msg.lower()
        if re.search(r'\bonline\b', lower):
            result['is_online'] = True
        elif re.search(r'\b(offline|in.?person)\b', lower):
            result['is_online'] = False

        # Negation must be checked before the positive pattern, otherwise
        # 'not recurring' matches `\brecurring\b` and gets flagged as True.
        if re.search(r'\b(not\s+recurring|one.?time|non.?recurring)\b', lower):
            result['is_recurring'] = False
        elif re.search(r'\b(recurring|repeating)\b', lower):
            result['is_recurring'] = True

        return result

    def _get_last_asked_field(self, history: list) -> Optional[str]:
        last_assistant = next(
            (m for m in reversed(history) if m["role"] == "assistant"), None,
        )
        if not last_assistant:
            return None
        content = last_assistant["content"]
        # Bot includes the exact FIELD_QUESTIONS template in every prompt;
        # exact-match avoids false positives from the "Got it. I have X..."
        # confirmation prefix that references the previous field.
        for field, question in FIELD_QUESTIONS.items():
            if question in content:
                return field
        lower = content.lower()
        for field, hints in FIELD_LAST_ASKED_HINTS.items():
            if any(hint in lower for hint in hints):
                return field
        return None

    def _parse_date_string(self, text: str) -> Optional[str]:
        m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
        if m:
            return m.group(1)
        m = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', text)
        if m:
            d, mo, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
            return f"{y}-{mo}-{d}"
        return None

    def _direct_parse(self, user_message: str, field: str) -> dict:
        result = {}
        msg = user_message.strip()
        if field in DATE_FIELDS:
            parsed = self._parse_date_string(msg)
            if parsed:
                result[field] = parsed
        elif field == 'time':
            m = re.search(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', msg)
            if m:
                result[field] = f"{int(m.group(1)):02d}:{m.group(2)}"
        elif field in ('ticket_limit', 'capacity'):
            m = re.search(r'\b(\d+)\b', msg)
            if m:
                result[field] = int(m.group(1))
        elif field == 'is_recurring':
            lower = msg.lower()
            if any(w in lower for w in ['no', 'false', 'nope', 'not recurring']):
                result[field] = False
            elif any(w in lower for w in ['yes', 'true', 'yeah', 'yep']):
                result[field] = True
        elif field == 'is_online':
            lower = msg.lower()
            if 'offline' in lower or 'in person' in lower or 'in-person' in lower:
                result[field] = False
            elif 'online' in lower:
                result[field] = True
            elif any(w in lower for w in ['no', 'false', 'nope']):
                result[field] = False
            elif any(w in lower for w in ['yes', 'true', 'yeah', 'yep']):
                result[field] = True
        elif field in ('name', 'venue_name', 'venue_address', 'organizer_name',
                       'recurrence_frequency', 'description', 'category', 'language'):
            result[field] = msg
        elif field == 'organizer_email':
            # Permissive: any token containing '@'. EmailStr decides validity
            # downstream — this lets us surface INVALID_INPUT for inputs like
            # "hello@not" instead of silently re-asking.
            m = re.search(r'\S*@\S*', msg)
            if m and m.group() != '@':
                result[field] = m.group()
        elif field == 'seat_types':
            seat_dict = self._parse_seat_types(msg)
            if seat_dict:
                result[field] = seat_dict
        return result

    def _parse_seat_types(self, text: str) -> Dict[str, float]:
        """Parse '\"VIP: 100k, Regular: 50k\"' into {'VIP': 100000, 'Regular': 50000}."""
        result: Dict[str, float] = {}
        for m in re.finditer(
            r'([A-Za-z][A-Za-z\s]+?)\s*[:=]\s*([\d,.]+)\s*(k|K|m|M)?',
            text,
        ):
            name = m.group(1).strip().title()
            raw = m.group(2).replace(',', '')
            try:
                value = float(raw)
            except ValueError:
                continue
            suffix = (m.group(3) or '').lower()
            if suffix == 'k':
                value *= 1000
            elif suffix == 'm':
                value *= 1_000_000
            result[name] = value
        return result

    def _validate_email_early(self, draft: dict, session_id: str) -> Optional[ChatResponse]:
        """Validate organizer_email as soon as it's in the draft. EventCreate
        only runs once every field is present, so without this check a value
        like 'hello@not' would silently fall through to MISSING_FIELD.
        """
        email = draft.get('organizer_email')
        if not email:
            return None
        try:
            _EMAIL_VALIDATOR.validate_python(email)
            return None
        except ValidationError as e:
            msg = e.errors()[0].get("msg", "value is not a valid email address")
            msg = msg.replace("Value error, ", "")
            draft.pop('organizer_email', None)
            session_service.set_draft(session_id, draft)
            message = self._generate_error_message('organizer_email', msg, draft)
            return ChatResponse(
                session_id=session_id, role="assistant",
                scenario=Scenario.INVALID_INPUT, message=message,
            )

    def _validate_dates_early(self, draft: dict, session_id: str) -> Optional[ChatResponse]:
        def parse(s):
            try:
                return datetime.strptime(s, "%Y-%m-%d")
            except Exception:
                return None

        event_date = parse(draft.get("date"))
        purchase_start = parse(draft.get("purchase_start"))
        purchase_end = parse(draft.get("purchase_end"))

        if purchase_start and event_date and purchase_start >= event_date:
            draft.pop("purchase_start", None)
            session_service.set_draft(session_id, draft)
            return ChatResponse(
                session_id=session_id, role="assistant",
                scenario=Scenario.INVALID_INPUT,
                message=(
                    f"Thanks for the info. The ticket sale start date must be before the "
                    f"event date ({draft.get('date')}). Could you provide a valid start date in "
                    f"YYYY-MM-DD format?"
                ),
            )

        if purchase_end and event_date and purchase_end >= event_date:
            draft.pop("purchase_end", None)
            session_service.set_draft(session_id, draft)
            return ChatResponse(
                session_id=session_id, role="assistant",
                scenario=Scenario.INVALID_INPUT,
                message=(
                    f"Thanks for the info. The ticket sale end date must be before the "
                    f"event date ({draft.get('date')}). Could you provide a valid end date in "
                    f"YYYY-MM-DD format?"
                ),
            )

        if purchase_start and purchase_end and purchase_end <= purchase_start:
            draft.pop("purchase_end", None)
            session_service.set_draft(session_id, draft)
            return ChatResponse(
                session_id=session_id, role="assistant",
                scenario=Scenario.INVALID_INPUT,
                message=(
                    f"Got it. The ticket sale end date must be after the start date "
                    f"({draft.get('purchase_start')}). Could you provide a valid end date in "
                    f"YYYY-MM-DD format?"
                ),
            )

        return None

    def _get_next_field(self, missing_fields: list) -> str:
        for field in FIELD_PRIORITY:
            if field not in missing_fields:
                continue
            if field == "recurrence_frequency":
                continue
            return field
        if 'recurrence_frequency' in missing_fields:
            return 'recurrence_frequency'
        return missing_fields[0] if missing_fields else "name"

    def _generate_question(
        self, field: str, draft: dict, prior_draft: Optional[dict] = None,
    ) -> str:
        """3-part: Acknowledge (only fields that changed this turn) + Ask next.

        When the user's input couldn't be parsed for the asked field, nothing
        in the draft changes, and we skip the ack to avoid the misleading
        'Got it. I have the {old field} as {old value}' that surfaces a stale
        value as if the user had just provided it.
        """
        question = FIELD_QUESTIONS.get(field, f"Please provide {field}.")
        prior_draft = prior_draft or {}
        changed = [
            f for f in FIELD_PRIORITY
            if f != field
            and draft.get(f) is not None
            and prior_draft.get(f) != draft.get(f)
        ]
        if not changed:
            return question
        ack_field = changed[-1]
        value = draft[ack_field]
        display = FIELD_DISPLAY_NAMES.get(ack_field, ack_field)
        return f"Got it. I have the {display} as {value!r}. {question}"

    def _generate_confirmation_message(
        self, draft: dict, acknowledgement: Optional[str] = None,
    ) -> str:
        ack = acknowledgement or "Thanks for all the details."
        lines = [ack, "", "Here's a summary of your event:"]
        for field in FIELD_PRIORITY:
            value = draft.get(field)
            if value is None:
                continue
            display = FIELD_DISPLAY_NAMES.get(field, field)
            lines.append(f"- {display}: {value}")
        lines.append("")
        lines.append("Shall I save this event? (yes/no)")
        return "\n".join(lines)

    def _generate_error_message(self, field: str, error_msg: str, draft: dict) -> str:
        """3-part: Acknowledge + Clarify error + Ask again."""
        display = FIELD_DISPLAY_NAMES.get(field, str(field))
        clean = error_msg.replace("Value error, ", "")
        question = FIELD_QUESTIONS.get(field, f"Please provide {field}.")
        return (
            f"Thanks for the input. The {display} you provided isn't valid: {clean}. "
            f"{question}"
        )


_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service


def reset_conversation_service() -> None:
    """Reset cached service (used in tests)."""
    global _conversation_service
    _conversation_service = None
