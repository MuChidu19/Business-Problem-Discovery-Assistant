import os
import pandas as pd
from datetime import datetime

# In-memory fallback storage if filesystem write fails (e.g., cloud/locked paths)
_FALLBACK_ROWS: list[dict] = []


REQUIRED_COLUMNS = [
    "Timestamp",
    "Employee_id",
    "Feedback",
    "FeedbackType",
    "OffDefinitions",
    "Suggestions",
    "Account",
    "Industry",
    "ProblemStatement",
    "Agent",
    "Section",
]


def _ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    for c in REQUIRED_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[REQUIRED_COLUMNS]


def append_feedback(csv_path: str, row: dict) -> None:
    row = {**{c: "" for c in REQUIRED_COLUMNS}, **row}
    if not row.get("Timestamp"):
        row["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            df = _ensure_schema(df)
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        else:
            # Ensure parent dir exists
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            df = pd.DataFrame([row], columns=REQUIRED_COLUMNS)
        df.to_csv(csv_path, index=False)
    except (PermissionError, OSError):
        # Store to in-memory fallback if disk write fails
        _FALLBACK_ROWS.append(row)


def read_feedback(csv_path: str) -> pd.DataFrame:
    file_df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    if os.path.exists(csv_path):
        try:
            file_df = _ensure_schema(pd.read_csv(csv_path))
        except Exception:
            file_df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    fb_df = pd.DataFrame(_FALLBACK_ROWS, columns=REQUIRED_COLUMNS) if _FALLBACK_ROWS else pd.DataFrame(columns=REQUIRED_COLUMNS)
    if not file_df.empty and not fb_df.empty:
        return pd.concat([file_df, fb_df], ignore_index=True)
    return file_df if not file_df.empty else fb_df
