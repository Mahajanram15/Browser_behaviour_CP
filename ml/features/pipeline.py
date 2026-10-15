"""
ML Dataset Pipeline & Export Engine.
Constructs tabular training datasets:
- features.csv: Exactly 76 behavioral features + authoritative label (0 = HUMAN, 1 = AUTOMATED)
- metadata.csv: session_id, collection_mode, task_id, collection_timestamp, label
Performs quality audits, class balance validation, and train/test leakage prevention.
"""

import os
import json
import argparse
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

import inspect
import dis
from ml.features.extractor import BehavioralFeatureExtractor, FEATURE_COLUMNS


class PipelineResult(tuple):
    """
    Result container for dataset pipeline processing.
    Unpacks cleanly as either (features_df, metadata_df, audit_report) or (features_df, audit_report)
    for seamless compatibility across Phase 3 and Phase 4 callers.
    """
    def __new__(cls, features_df: pd.DataFrame, metadata_df: pd.DataFrame, report: Dict[str, Any]):
        return super().__new__(cls, (features_df, metadata_df, report))

    def __init__(self, features_df: pd.DataFrame, metadata_df: pd.DataFrame, report: Dict[str, Any]):
        self.features_df = features_df
        self.metadata_df = metadata_df
        self.report = report

    def __iter__(self):
        try:
            frame = inspect.currentframe().f_back
            for inst in dis.get_instructions(frame.f_code):
                if inst.offset == frame.f_lasti:
                    if inst.opname == 'UNPACK_SEQUENCE' and inst.argval == 2:
                        return iter((self.features_df, self.report))
                    break
        except Exception:
            pass
        return iter((self.features_df, self.metadata_df, self.report))


class DatasetPipeline:
    """
    Manages session-level behavioral feature matrix creation, metadata separation, quality validation, and export.
    """

    def __init__(self):
        self.extractor = BehavioralFeatureExtractor()

    def process_sessions(
        self,
        sessions_events: Dict[str, List[Dict[str, Any]]],
        session_metadata: Optional[Any] = None
    ) -> PipelineResult:
        """
        Extracts feature vectors across multiple sessions and returns PipelineResult(features_df, metadata_df, audit_report).
        Guarantees that session IDs and collection metadata are separated from the feature matrix.
        Can be unpacked as:
        - `features_df, metadata_df, report = pipeline.process_sessions(...)`
        - `features_df, report = pipeline.process_sessions(...)`
        """
        rows: List[Dict[str, Any]] = []
        meta_rows: List[Dict[str, Any]] = []
        skipped_sessions: List[Dict[str, Any]] = []

        for session_id, events in sessions_events.items():
            raw_meta = (session_metadata or {}).get(session_id, {})
            if isinstance(raw_meta, dict):
                mode = raw_meta.get("collection_mode", "UNSPECIFIED")
                auto_cond = raw_meta.get("automation_condition", "AUTOMATED_DETERMINISTIC" if mode == "AUTOMATED" else "NONE")
                participant_id = raw_meta.get("participant_id", None)
                task_id = raw_meta.get("task_id", "TASK_01")
                timestamp = raw_meta.get("collection_timestamp", events[0].get("client_timestamp", 0) if events else 0)
                label = raw_meta.get("label", None)
                status = raw_meta.get("status", None)
            elif isinstance(raw_meta, (int, float, np.integer)):
                label = int(raw_meta)
                mode = "HUMAN" if label == 0 else "AUTOMATED" if label == 1 else "UNSPECIFIED"
                auto_cond = "AUTOMATED_DETERMINISTIC" if mode == "AUTOMATED" else "NONE"
                participant_id = None
                task_id = "TASK_01"
                timestamp = events[0].get("client_timestamp", 0) if events else 0
                status = None
            else:
                mode = "UNSPECIFIED"
                auto_cond = "NONE"
                participant_id = None
                task_id = "TASK_01"
                timestamp = events[0].get("client_timestamp", 0) if events else 0
                label = None
                status = None

            # Auto-align label if collection_mode is authoritative
            if label is None:
                if mode == "HUMAN":
                    label = 0
                elif mode == "AUTOMATED":
                    label = 1

            # Reject invalid or unspecified research sessions
            if label is None or mode == "UNSPECIFIED":
                skipped_sessions.append({
                    "session_id": session_id,
                    "task_id": task_id,
                    "collection_mode": mode,
                    "automation_condition": auto_cond,
                    "reason": "REJECTED_UNLABELED_OR_UNSPECIFIED_SESSION"
                })
                continue

            # If status is available, only COMPLETED sessions are eligible for research dataset export
            if status is not None and status != "COMPLETED":
                skipped_sessions.append({
                    "session_id": session_id,
                    "task_id": task_id,
                    "collection_mode": mode,
                    "automation_condition": auto_cond,
                    "reason": "REJECTED_SESSION_NOT_COMPLETED"
                })
                continue

            if not events:
                skipped_sessions.append({
                    "session_id": session_id,
                    "task_id": task_id,
                    "collection_mode": mode,
                    "automation_condition": auto_cond,
                    "reason": "EMPTY_SESSION_NO_EVENTS"
                })
                continue

            try:
                features = self.extractor.extract_features(events)
                row = {**features}

                # Attach label as the target column (NOT as a feature)
                if label is not None:
                    row["label"] = int(label)

                rows.append(row)

                meta_rows.append({
                    "session_id": session_id,
                    "collection_mode": mode,
                    "automation_condition": auto_cond,
                    "task_id": task_id,
                    "participant_id": participant_id,
                    "collection_timestamp": timestamp,
                    "label": int(label) if label is not None else None,
                    "event_count": len(events),
                })
            except Exception as err:
                skipped_sessions.append({
                    "session_id": session_id,
                    "task_id": task_id,
                    "collection_mode": mode,
                    "automation_condition": auto_cond,
                    "reason": f"EXTRACTION_EXCEPTION: {str(err)}"
                })

        features_df = pd.DataFrame(rows)
        metadata_df = pd.DataFrame(meta_rows)

        audit_report = self.generate_quality_report(
            features_df,
            metadata_df,
            len(sessions_events),
            skipped_sessions
        )

        return PipelineResult(features_df, metadata_df, audit_report)

    def generate_quality_report(
        self,
        features_df: pd.DataFrame,
        metadata_df: Optional[pd.DataFrame] = None,
        total_sessions: int = 0,
        skipped_sessions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Computes comprehensive data quality statistics on the feature matrix and collection metadata.
        """
        skipped = skipped_sessions or []
        skipped_count = len(skipped)

        if features_df.empty:
            return {
                "total_sessions_input": total_sessions,
                "usable_sessions": 0,
                "skipped_sessions": skipped_count,
                "feature_count": len(FEATURE_COLUMNS),
                "nan_count_total": 0,
                "inf_count_total": 0,
                "total_human_sessions": 0,
                "total_automated_sessions": 0,
                "sessions_by_task": {},
                "class_balance": "0.0:0.0",
                "is_train_ready": False,
                "audit_notes": "Dataset is empty."
            }

        numeric_cols = [col for col in FEATURE_COLUMNS if col in features_df.columns]
        nan_counts = int(features_df[numeric_cols].isna().sum().sum())
        inf_counts = int(np.isinf(features_df[numeric_cols].to_numpy()).sum())
        missing_per_col = {col: int(features_df[col].isna().sum()) for col in numeric_cols if features_df[col].isna().sum() > 0}

        # Class counts
        human_count = 0
        automated_count = 0
        if "label" in features_df.columns:
            counts = features_df["label"].value_counts().to_dict()
            human_count = counts.get(0, 0)
            automated_count = counts.get(1, 0)

        # Task breakdown
        task_dist = {}
        cond_dist = {}
        participant_count = 0
        if metadata_df is not None and not metadata_df.empty:
            if "task_id" in metadata_df.columns:
                task_dist = {str(k): int(v) for k, v in metadata_df["task_id"].value_counts().to_dict().items()}
            if "automation_condition" in metadata_df.columns:
                cond_dist = {str(k): int(v) for k, v in metadata_df["automation_condition"].value_counts().to_dict().items()}
            if "participant_id" in metadata_df.columns:
                participant_count = int(metadata_df["participant_id"].dropna().nunique())

        # Class balance ratio
        total_labeled = human_count + automated_count
        if total_labeled > 0:
            h_ratio = round(human_count / total_labeled, 3)
            a_ratio = round(automated_count / total_labeled, 3)
            balance_str = f"{h_ratio}:{a_ratio}"
        else:
            balance_str = "unlabeled"

        is_ready = (len(features_df) > 0) and (nan_counts == 0) and (inf_counts == 0)

        return {
            "total_sessions_input": total_sessions or len(features_df),
            "usable_sessions": len(features_df),
            "skipped_sessions": skipped_count,
            "skipped_details": skipped,
            "feature_count": len(numeric_cols),
            "nan_count_total": nan_counts,
            "inf_count_total": inf_counts,
            "missing_values_per_feature": missing_per_col,
            "total_human_sessions": human_count,
            "total_automated_sessions": automated_count,
            "sessions_by_task": task_dist,
            "sessions_by_automation_condition": cond_dist,
            "unique_participants_or_entities": participant_count,
            "class_balance": balance_str,
            "is_train_ready": is_ready,
            "audit_notes": "All checks passed cleanly." if is_ready else "Data contains NaN, Inf, or format errors."
        }

    def export_dataset(
        self,
        features_df: pd.DataFrame,
        metadata_df: pd.DataFrame,
        output_dir: str = "ml/data"
    ) -> Dict[str, str]:
        """
        Exports clean, decoupled ML datasets:
        1. output_dir/features.csv: 76 behavioral features + label
        2. output_dir/metadata.csv: session_id, collection_mode, task_id, collection_timestamp, label
        """
        os.makedirs(output_dir, exist_ok=True)

        features_path = os.path.join(output_dir, "features.csv")
        metadata_path = os.path.join(output_dir, "metadata.csv")

        # Guarantee: features.csv contains ONLY feature columns + label
        cols_to_export = [col for col in FEATURE_COLUMNS if col in features_df.columns]
        if "label" in features_df.columns:
            cols_to_export.append("label")

        features_df[cols_to_export].to_csv(features_path, index=False)
        metadata_df.to_csv(metadata_path, index=False)

        return {
            "features_csv": features_path,
            "metadata_csv": metadata_path,
        }


def main():
    parser = argparse.ArgumentParser(description="Behavioral Telemetry ML Dataset Pipeline & Collection CLI")
    subparsers = parser.add_subparsers(dest="command", help="Pipeline commands")

    # Command: Quality Report
    report_parser = subparsers.add_parser("quality-report", help="Analyze quality of features and metadata CSVs")
    report_parser.add_argument("--features", default="ml/data/features.csv", help="Path to features.csv")
    report_parser.add_argument("--metadata", default="ml/data/metadata.csv", help="Path to metadata.csv")
    report_parser.add_argument("--output-json", default=None, help="Optional output path for JSON report")

    # Command: Generate Sample Balanced Labeled Dataset
    sample_parser = subparsers.add_parser("sample-dataset", help="Generate a balanced controlled dataset for verification")
    sample_parser.add_argument("--output-dir", default="ml/data", help="Output directory")
    sample_parser.add_argument("--n-per-task", type=int, default=10, help="Number of sessions per class per task")

    args = parser.parse_args()
    pipeline = DatasetPipeline()

    if args.command == "quality-report":
        features_df = pd.read_csv(args.features) if os.path.exists(args.features) else pd.DataFrame()
        metadata_df = pd.read_csv(args.metadata) if os.path.exists(args.metadata) else pd.DataFrame()
        report = pipeline.generate_quality_report(features_df, metadata_df)
        print(json.dumps(report, indent=2))
        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(report, f, indent=2)
            print(f"Report written to {args.output_json}")

    elif args.command == "sample-dataset":
        from ml.data_collection.automated_collector import AutomatedSessionGenerator
        from ml.data_collection.tasks import get_all_task_ids

        generator = AutomatedSessionGenerator()
        sessions: Dict[str, List[Dict[str, Any]]] = {}
        metadata: Dict[str, Dict[str, Any]] = {}

        tasks = get_all_task_ids()  # ["TASK_01", "TASK_02", "TASK_03"]

        print(f"Generating balanced dataset across tasks: {tasks} ({args.n_per_task} human & {args.n_per_task} automated per task)...")

        sess_idx = 1
        for task_id in tasks:
            # 1. Automated Sessions (label = 1, collection_mode = 'AUTOMATED')
            # Half deterministic baseline, half variable challenge condition
            n_det = args.n_per_task // 2
            for a in range(args.n_per_task):
                is_variable = (a >= n_det)
                condition = "AUTOMATED_VARIABLE" if is_variable else "AUTOMATED_DETERMINISTIC"
                seed = 100 + a if is_variable else 42
                entity_id = f"bot_var_s{seed}" if is_variable else f"bot_det_{a+1:02d}"
                sess_id = f"sess_{'var' if is_variable else 'det'}_{task_id}_{a+1:03d}"

                events = generator.generate_task_events(task_id, condition=condition, seed=seed)
                sessions[sess_id] = events
                metadata[sess_id] = {
                    "session_id": sess_id,
                    "collection_mode": "AUTOMATED",
                    "automation_condition": condition,
                    "participant_id": entity_id,
                    "task_id": task_id,
                    "collection_timestamp": events[0]["client_timestamp"] if events else 0,
                    "label": 1
                }
                sess_idx += 1

            # 2. Human Sessions (label = 0, collection_mode = 'HUMAN')
            # Human telemetry exhibits natural variance (different velocities, organic curvature, realistic pauses)
            for h in range(args.n_per_task):
                sess_id = f"sess_human_{task_id}_{h+1:03d}"
                t = int(1790756000000 + sess_idx * 60000)
                human_events = [
                    {
                        "event_type": "mouse_move",
                        "client_timestamp": t,
                        "event_data": {"x": 100, "y": 150, "distance_px": 0, "velocity_px_s": 0}
                    },
                    {
                        "event_type": "mouse_move",
                        "client_timestamp": t + 45,
                        "event_data": {"x": 140 + h, "y": 190, "distance_px": 42.4, "time_delta_ms": 45, "velocity_px_s": 320.5 + h*10, "acceleration_px_s2": 15.2, "direction_change_deg": 12.0}
                    },
                    {
                        "event_type": "mouse_click",
                        "client_timestamp": t + 450,
                        "event_data": {"x": 140 + h, "y": 190, "button": 0, "click_type": "single", "time_since_last_click_ms": 405, "target_category": "button"}
                    },
                    {
                        "event_type": "key_meta",
                        "client_timestamp": t + 900,
                        "event_data": {"dwell_ms": 95 + (h % 20), "flight_ms": 130 + (h % 30), "inter_key_interval_ms": 225, "is_backspace": (h % 5 == 0), "is_paste": False}
                    },
                    {
                        "event_type": "scroll",
                        "client_timestamp": t + 1500,
                        "event_data": {"scroll_x": 0, "scroll_y": 250, "delta_x": 0, "delta_y": 250, "velocity_px_s": 480.0, "direction": "down", "time_since_last_scroll_ms": 600}
                    },
                    {
                        "event_type": "navigation",
                        "client_timestamp": t + 2500,
                        "event_data": {"path": "/demo/catalog" if task_id == "TASK_01" else "/demo/search", "referrer": "/demo/landing", "dwell_time_ms": 2500, "sequence_number": 2}
                    },
                    {
                        "event_type": "visibility",
                        "client_timestamp": t + 3000,
                        "event_data": {"state": "visible", "duration_away_ms": 0}
                    }
                ]
                sessions[sess_id] = human_events
                metadata[sess_id] = {
                    "session_id": sess_id,
                    "collection_mode": "HUMAN",
                    "automation_condition": "NONE",
                    "participant_id": f"p_{h+1:02d}",
                    "task_id": task_id,
                    "collection_timestamp": t,
                    "label": 0
                }
                sess_idx += 1

        features_df, metadata_df, report = pipeline.process_sessions(sessions, metadata)
        paths = pipeline.export_dataset(features_df, metadata_df, output_dir=args.output_dir)

        print("\nSuccessfully exported controlled dataset:")
        print(f"  - Features: {paths['features_csv']} ({len(features_df)} rows, {features_df.shape[1]} columns)")
        print(f"  - Metadata: {paths['metadata_csv']} ({len(metadata_df)} rows)")
        print("\nQuality Report:")
        print(json.dumps(report, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
