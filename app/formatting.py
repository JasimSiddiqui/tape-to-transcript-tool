"""Turning stored segments into readable text."""

# Plain-text transcripts start a new paragraph after about this many seconds.
PARAGRAPH_SECONDS = 60

# Prepended by "Copy with Prompt" so the transcript can be pasted straight into an AI chat.
SUMMARY_PROMPT = (
    "Below is a transcript of a course lecture. Summarize the key concepts, "
    "definitions, and any examples, organized by topic.\n\n"
)


def format_timestamp(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def format_duration(seconds):
    seconds = int(round(seconds or 0))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def build_text(segments, include_timestamps=False):
    """segments: list of (start, end, text). Returns the transcript as plain text."""
    if include_timestamps:
        return "\n".join(f"[{format_timestamp(start)}] {text}" for start, _end, text in segments)

    # Whisper segment times stretch over pauses, so instead of detecting silences
    # we break roughly every minute, at the end of a sentence.
    paragraphs = []
    current = []
    paragraph_start = 0.0
    for start, _end, text in segments:
        if not current:
            paragraph_start = start
        current.append(text)
        if start - paragraph_start >= PARAGRAPH_SECONDS and text.endswith((".", "?", "!")):
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)
