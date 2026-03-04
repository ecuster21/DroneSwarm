"""Helpers for writing runtime auction metrics to JSONL files."""

from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
from typing import Dict
from typing import Optional


def _timestamp_token(timestamp: Optional[str] = None) -> str:
    """Return a filesystem-friendly UTC timestamp token."""
    value = (
        timestamp
        or datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    )
    return value.replace(':', '-').replace('.', '-')


class MetricsLogWriter:
    """Append JSONL metric events for one recorder instance."""

    def __init__(
        self,
        output_dir: str,
        profile_name: str,
        namespace: str = '',
        session_label: str = '',
        timestamp: Optional[str] = None,
    ) -> None:
        """Create the output file path and ensure the directory exists."""
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.profile_name = profile_name
        self.namespace = namespace
        self.session_label = session_label
        namespace_token = namespace.replace('/', '_') if namespace else 'global'
        label_suffix = f'_{session_label}' if session_label else ''
        filename = (
            f'{profile_name}_{namespace_token}{label_suffix}_'
            f'{_timestamp_token(timestamp)}.jsonl'
        )
        self.file_path = self.output_dir / filename

    def append(
        self,
        source_topic: str,
        payload: str,
        timestamp: Optional[str] = None,
    ) -> Dict:
        """Append one event and return the event dictionary."""
        event = {
            'recorded_at_utc': (
                timestamp
                or datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            ),
            'profile_name': self.profile_name,
            'namespace': self.namespace,
            'source_topic': source_topic,
            'payload': payload,
        }
        with self.file_path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, sort_keys=True) + '\n')
        return event
