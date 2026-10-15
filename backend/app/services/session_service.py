import hashlib
import uuid
import os
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from backend.app.schemas.session import SessionStartRequest, SessionStartResponse, SessionEndResponse
from backend.app.schemas.behavior import BehaviorBatchRequest, BehaviorBatchResponse
from backend.app.schemas.api_log import ApiRequestCreate, ApiRequestResponse

class SessionService:
    """
    Session Service handling session lifecycle, event ingestion, and labeled dataset collection.
    Supports asynchronous PostgreSQL persistence with transparent in-memory fallback.
    """
    def __init__(self):
        self._lock = threading.Lock()
        # In-memory registry for sessions, events, and API telemetry
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._events_count: Dict[str, int] = {}
        self._events_by_session: Dict[str, List[Dict[str, Any]]] = {}
        self._api_requests: Dict[str, List[Dict[str, Any]]] = {}
        self._api_requests_count: Dict[str, int] = {}
        self._global_request_id: int = 0
        self._load_cache()

    def _get_cache_path(self) -> str:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        return os.path.join(root_dir, "ml", "data", ".active_sessions_cache.json")

    def _load_cache(self) -> None:
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._sessions = data.get("_sessions", {})
                    self._events_count = data.get("_events_count", {})
                    self._events_by_session = data.get("_events_by_session", {})
                    self._api_requests = data.get("_api_requests", {})
                    self._api_requests_count = data.get("_api_requests_count", {})
                    self._global_request_id = data.get("_global_request_id", 0)
                    if not self._global_request_id and self._api_requests:
                        max_id = 0
                        for reqs in self._api_requests.values():
                            for r in reqs:
                                max_id = max(max_id, r.get("request_id", 0))
                        self._global_request_id = max_id
                    for s in self._sessions.values():
                        if isinstance(s.get("start_time"), str):
                            try:
                                s["start_time"] = datetime.fromisoformat(s["start_time"])
                            except Exception:
                                pass
                        if isinstance(s.get("end_time"), str):
                            try:
                                s["end_time"] = datetime.fromisoformat(s["end_time"])
                            except Exception:
                                pass
            except Exception as e:
                print(f"[SessionService Cache Warning] Failed to load sessions cache: {e}")

    def _save_cache(self) -> None:
        cache_path = self._get_cache_path()
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            serializable_sessions = {}
            for s_id, s in self._sessions.items():
                s_copy = dict(s)
                if isinstance(s_copy.get("start_time"), datetime):
                    s_copy["start_time"] = s_copy["start_time"].isoformat()
                if isinstance(s_copy.get("end_time"), datetime):
                    s_copy["end_time"] = s_copy["end_time"].isoformat()
                serializable_sessions[s_id] = s_copy

            snapshot = {
                "_sessions": serializable_sessions,
                "_events_count": self._events_count,
                "_events_by_session": self._events_by_session,
                "_api_requests": self._api_requests,
                "_api_requests_count": self._api_requests_count,
                "_global_request_id": self._global_request_id,
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
        except Exception as e:
            print(f"[SessionService Cache Warning] Failed to save sessions cache: {e}")

    def generate_session_id(self) -> str:
        return f"sess_{uuid.uuid4().hex[:20]}"

    def hash_ip(self, ip: str) -> str:
        return hashlib.sha256(ip.encode("utf-8")).hexdigest()

    async def create_session(
        self,
        req: SessionStartRequest,
        client_ip: str,
        db: Optional[Any] = None
    ) -> SessionStartResponse:
        session_id = self.generate_session_id()
        now = datetime.utcnow()
        ip_hash_val = self.hash_ip(client_ip)

        collection_mode = req.collection_mode or "UNSPECIFIED"
        task_id = req.task_id or "TASK_01"
        auto_cond = req.automation_condition or ("AUTOMATED_DETERMINISTIC" if collection_mode == "AUTOMATED" else "NONE")
        participant_id = req.participant_id

        # Explicit label assignment based on authoritative collection mode
        label = req.label
        if label is None:
            if collection_mode == "HUMAN":
                label = 0
            elif collection_mode == "AUTOMATED":
                label = 1

        # In-memory record
        self._sessions[session_id] = {
            "session_id": session_id,
            "user_agent": req.user_agent,
            "ip_hash": ip_hash_val,
            "start_time": now,
            "status": "ACTIVE",
            "screen_resolution": req.screen_resolution,
            "client_timezone": req.client_timezone,
            "collection_mode": collection_mode,
            "automation_condition": auto_cond,
            "participant_id": participant_id,
            "task_id": task_id,
            "label": label,
            "collection_timestamp": int(now.timestamp() * 1000),
        }
        self._events_count[session_id] = 0
        self._events_by_session[session_id] = []
        self._api_requests[session_id] = []
        self._api_requests_count[session_id] = 0
        self._save_cache()

        # PostgreSQL persistence if DB session is active
        if db is not None:
            try:
                from backend.app.models.session import SessionModel
                db_session = SessionModel(
                    session_id=session_id,
                    user_agent=req.user_agent,
                    ip_hash=ip_hash_val,
                    start_time=now,
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )
                db.add(db_session)
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"[SessionService DB Warning] Could not persist session to PostgreSQL: {e}")

        return SessionStartResponse(
            session_id=session_id,
            status="ACTIVE",
            start_time=now,
        )

    async def record_events(
        self,
        req: BehaviorBatchRequest,
        db: Optional[Any] = None
    ) -> BehaviorBatchResponse:
        session_id = req.session_id
        now = datetime.utcnow()

        if session_id not in self._sessions:
            return BehaviorBatchResponse(
                session_id=session_id,
                processed_events=0,
                status="DISCARDED_UNKNOWN_SESSION",
            )

        raw_events = [ev.model_dump() if hasattr(ev, "model_dump") else ev.dict() for ev in req.events]
        self._events_by_session[session_id].extend(raw_events)

        count = len(req.events)
        self._events_count[session_id] = self._events_count.get(session_id, 0) + count
        self._save_cache()

        # PostgreSQL batch insert if DB is active
        if db is not None:
            try:
                from backend.app.models.behavior import BehaviorEventModel
                event_records = [
                    BehaviorEventModel(
                        session_id=session_id,
                        event_type=ev.event_type,
                        client_timestamp=ev.client_timestamp,
                        server_timestamp=now,
                        event_data=ev.event_data,
                    )
                    for ev in req.events
                ]
                db.add_all(event_records)
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"[SessionService DB Warning] Could not persist events to PostgreSQL: {e}")

        return BehaviorBatchResponse(
            session_id=session_id,
            processed_events=count,
            status="INGESTED",
        )

    async def record_api_request(
        self,
        req: ApiRequestCreate,
        db: Optional[Any] = None
    ) -> ApiRequestResponse:
        session_id = req.session_id
        now = datetime.utcnow()

        if session_id not in self._sessions:
            return ApiRequestResponse(
                request_id=0,
                session_id=session_id,
                status="DISCARDED_UNKNOWN_SESSION",
                sequence_number=0,
            )

        with self._lock:
            self._global_request_id += 1
            request_id = self._global_request_id
            current_seq = self._api_requests_count.get(session_id, 0) + 1
            self._api_requests_count[session_id] = current_seq

            client_ts = req.client_timestamp
            server_ts = int(now.timestamp() * 1000)

            record = {
                "request_id": request_id,
                "session_id": session_id,
                "sequence_number": current_seq,
                "endpoint": req.endpoint,
                "http_method": req.http_method,
                "status_code": req.status_code,
                "response_time_ms": req.response_time_ms,
                "request_size_bytes": req.request_size_bytes or 0,
                "response_size_bytes": req.response_size_bytes or 0,
                "headers_fingerprint": req.headers_fingerprint,
                "payload_structure_hash": req.payload_structure_hash,
                "param_keys": req.param_keys or [],
                "payload_keys": req.payload_keys or [],
                "client_timestamp": client_ts,
                "timestamp": now.isoformat(),
                "server_timestamp": server_ts,
            }

            if session_id not in self._api_requests:
                self._api_requests[session_id] = []
            self._api_requests[session_id].append(record)
            self._save_cache()

        # PostgreSQL persistence if DB session is active
        if db is not None:
            try:
                from backend.app.models.api_log import ApiRequestModel
                db_record = ApiRequestModel(
                    session_id=session_id,
                    sequence_number=current_seq,
                    endpoint=req.endpoint,
                    http_method=req.http_method,
                    status_code=req.status_code,
                    response_time_ms=req.response_time_ms,
                    request_size_bytes=req.request_size_bytes or 0,
                    response_size_bytes=req.response_size_bytes or 0,
                    headers_fingerprint=req.headers_fingerprint,
                    payload_structure_hash=req.payload_structure_hash,
                    param_keys=req.param_keys or [],
                    payload_keys=req.payload_keys or [],
                    client_timestamp=client_ts,
                    timestamp=now,
                )
                db.add(db_record)
                await db.commit()
                await db.refresh(db_record)
                request_id = db_record.request_id
            except Exception as e:
                await db.rollback()
                print(f"[SessionService DB Warning] Could not persist API request to PostgreSQL: {e}")

        return ApiRequestResponse(
            request_id=request_id,
            session_id=session_id,
            status="RECORDED",
            sequence_number=current_seq,
        )

    async def end_session(
        self,
        session_id: str,
        end_reason: str = "USER_EXIT",
        collection_mode: Optional[str] = None,
        automation_condition: Optional[str] = None,
        participant_id: Optional[str] = None,
        task_id: Optional[str] = None,
        label: Optional[int] = None,
        db: Optional[Any] = None
    ) -> SessionEndResponse:
        session = self._sessions.get(session_id)
        now = datetime.utcnow()

        if session:
            start_time = session.get("start_time", now)
            duration = max(0.0, (now - start_time).total_seconds())
            session["status"] = "COMPLETED"
            session["end_time"] = now

            if collection_mode:
                session["collection_mode"] = collection_mode
            if automation_condition:
                session["automation_condition"] = automation_condition
            if participant_id:
                session["participant_id"] = participant_id
            if task_id:
                session["task_id"] = task_id
            if label is not None:
                session["label"] = label
            elif session.get("collection_mode") == "HUMAN":
                session["label"] = 0
            elif session.get("collection_mode") == "AUTOMATED":
                session["label"] = 1

            events_count = self._events_count.get(session_id, 0)
            self._save_cache()
        else:
            duration = 0.0
            events_count = 0

        # Trigger feature extraction and persistence
        events = self._events_by_session.get(session_id, [])
        if events:
            try:
                from backend.app.services.feature_engineering import feature_engineering_service
                await feature_engineering_service.compute_and_save_features(session_id, events, db=db)
            except Exception as e:
                print(f"[SessionService Feature Warning] Extraction error: {e}")

        if db is not None:
            try:
                from sqlalchemy import select
                from backend.app.models.session import SessionModel
                stmt = select(SessionModel).where(SessionModel.session_id == session_id)
                res = await db.execute(stmt)
                db_sess = res.scalar_one_or_none()
                if db_sess:
                    db_sess.status = "COMPLETED"
                    db_sess.end_time = now
                    db_sess.updated_at = now
                    await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"[SessionService DB Warning] Could not update session in PostgreSQL: {e}")

        return SessionEndResponse(
            session_id=session_id,
            status="COMPLETED",
            duration_seconds=round(duration, 2),
            total_events_captured=events_count,
            final_integrity_score=0.15,
        )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        return self._sessions

    def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        return self._events_by_session.get(session_id, [])

    def get_all_session_events(self) -> Dict[str, List[Dict[str, Any]]]:
        return self._events_by_session

    def get_session_api_requests(self, session_id: str) -> List[Dict[str, Any]]:
        return self._api_requests.get(session_id, [])

    def get_all_api_requests(self) -> Dict[str, List[Dict[str, Any]]]:
        return self._api_requests

    def get_api_requests_count(self, session_id: Optional[str] = None) -> int:
        if session_id:
            return self._api_requests_count.get(session_id, 0)
        return sum(self._api_requests_count.values())

    def get_dataset_summary(self) -> Dict[str, Any]:
        """
        Summarizes current in-memory collection statistics (human vs automated, tasks, conditions).
        """
        human_count = 0
        auto_count = 0
        task_dist: Dict[str, int] = {}
        cond_dist: Dict[str, int] = {}
        participants = set()

        for s in self._sessions.values():
            mode = s.get("collection_mode", "UNSPECIFIED")
            task = s.get("task_id", "TASK_01")
            cond = s.get("automation_condition", "NONE")
            p_id = s.get("participant_id")
            if p_id:
                participants.add(p_id)

            task_dist[task] = task_dist.get(task, 0) + 1
            cond_dist[cond] = cond_dist.get(cond, 0) + 1

            if mode == "HUMAN" or s.get("label") == 0:
                human_count += 1
            elif mode == "AUTOMATED" or s.get("label") == 1:
                auto_count += 1

        return {
            "total_sessions": len(self._sessions),
            "human_sessions": human_count,
            "automated_sessions": auto_count,
            "sessions_by_task": task_dist,
            "sessions_by_condition": cond_dist,
            "unique_participants": len(participants),
            "is_balanced": abs(human_count - auto_count) <= max(2, int(0.2 * max(human_count, auto_count, 1)))
        }

    def export_dataset(self, output_dir: str = "ml/data") -> Dict[str, Any]:
        """
        Exports in-memory collected sessions to ml/data/features.csv and ml/data/metadata.csv.
        """
        from ml.features.pipeline import DatasetPipeline
        pipeline = DatasetPipeline()
        sessions_events = self.get_all_session_events()
        metadata = {
            s_id: {
                "session_id": s_id,
                "collection_mode": s.get("collection_mode", "UNSPECIFIED"),
                "automation_condition": s.get("automation_condition", "AUTOMATED_DETERMINISTIC" if s.get("collection_mode") == "AUTOMATED" else "NONE"),
                "participant_id": s.get("participant_id"),
                "task_id": s.get("task_id", "TASK_01"),
                "collection_timestamp": s.get("collection_timestamp", 0),
                "label": s.get("label"),
                "status": s.get("status"),
            }
            for s_id, s in self._sessions.items()
        }

        features_df, metadata_df, report = pipeline.process_sessions(sessions_events, metadata)
        paths = pipeline.export_dataset(features_df, metadata_df, output_dir=output_dir)
        return {
            "paths": paths,
            "report": report,
            "usable_sessions": len(features_df)
        }

session_service = SessionService()
