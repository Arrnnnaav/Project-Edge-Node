from app.schema import Meta


def to_text(log: Meta) -> str:

    if log.total_meetings == 0:
        meetings = "no meetings"
    elif log.total_meetings == 1:
        meetings = "1 meeting"
    else:
        meetings = (
            f"{log.total_meetings} meetings with an average gap of "
            f"{log.average_gap_between_meetings_minutes:g} minutes between them"
        )

    msg_word = "message" if log.messages_sent_after_8pm == 1 else "messages"

    return (
        f"On {log.date.isoformat()}, user {log.user_id} had {meetings}, "
        f"totalling {log.meeting_hours_per_day:g} hours in meetings. "
        f"They sent {log.messages_sent_after_8pm} {msg_word} after 8pm and "
        f"switched work context {log.context_switches_per_hour} times per hour."
    )