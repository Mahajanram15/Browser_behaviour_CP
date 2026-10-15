import hashlib
import json
from typing import Optional, List, Any
from urllib.parse import urlsplit, parse_qs
from pydantic import BaseModel, Field, ConfigDict, model_validator

class ApiRequestCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str = Field(..., min_length=1, max_length=64, description="Bound session identifier")
    endpoint: str = Field(..., min_length=1, max_length=255, description="Accessed API endpoint path")
    http_method: str = Field(..., min_length=3, max_length=10, description="HTTP Method (GET, POST, etc.)")
    status_code: int = Field(..., ge=100, le=599, description="HTTP Response status code")
    response_time_ms: float = Field(..., ge=0.0, description="Server processing response duration in ms")
    request_size_bytes: Optional[int] = Field(default=0, ge=0, description="Request size in bytes")
    response_size_bytes: Optional[int] = Field(default=0, ge=0, description="Response size in bytes")
    headers_fingerprint: Optional[str] = Field(default=None, max_length=64, description="Fingerprint hash of headers structure")
    payload_structure_hash: Optional[str] = Field(default=None, max_length=64, description="Fingerprint hash of body structure")
    timestamp: Optional[int] = Field(default=None, description="Epoch ms timestamp")
    client_timestamp: Optional[int] = Field(default=None, description="Browser-side client timestamp in epoch ms")
    sequence_number: Optional[int] = Field(default=None, description="Monotonically increasing sequence number within session")
    param_keys: Optional[List[str]] = Field(default_factory=list, description="Parameter names only; never store parameter values")
    payload_keys: Optional[List[str]] = Field(default_factory=list, description="JSON body field names only; never store payload values")

    # Transient input helpers: parsed for keys only, NEVER persisted
    query_params: Optional[Any] = Field(default=None, exclude=True, description="Query parameters dictionary or list; parsed for keys only")
    raw_payload: Optional[Any] = Field(default=None, exclude=True, description="Raw JSON body; parsed for field names only")
    headers: Optional[Any] = Field(default=None, exclude=True, description="Raw headers dict; used for fingerprint calculation only")

    @model_validator(mode="after")
    def enforce_privacy_and_normalize(self):
        # 1. Parameter keys: extract parameter names only
        p_keys = list(self.param_keys or [])
        if self.query_params is not None:
            if isinstance(self.query_params, dict):
                p_keys.extend(str(k) for k in self.query_params.keys())
            elif isinstance(self.query_params, (list, tuple)):
                for item in self.query_params:
                    if isinstance(item, (list, tuple)) and len(item) > 0:
                        p_keys.append(str(item[0]))
                    elif isinstance(item, dict):
                        p_keys.extend(str(k) for k in item.keys())
            elif isinstance(self.query_params, str):
                qs = parse_qs(self.query_params.lstrip("?"), keep_blank_values=True)
                p_keys.extend(str(k) for k in qs.keys())

        # Parse query params from endpoint URL if present, and sanitize endpoint to path only
        parsed = urlsplit(self.endpoint)
        if parsed.query:
            qs = parse_qs(parsed.query, keep_blank_values=True)
            p_keys.extend(str(k) for k in qs.keys())
            self.endpoint = parsed.path if parsed.path else "/"

        seen_p = set()
        self.param_keys = [k for k in p_keys if not (k in seen_p or seen_p.add(k))]

        # 2. Payload keys: extract JSON body field names only
        pl_keys = list(self.payload_keys or [])
        if self.raw_payload is not None:
            if isinstance(self.raw_payload, dict):
                pl_keys.extend(str(k) for k in self.raw_payload.keys())
            elif isinstance(self.raw_payload, list):
                for item in self.raw_payload:
                    if isinstance(item, dict):
                        pl_keys.extend(str(k) for k in item.keys())

        seen_pl = set()
        self.payload_keys = [k for k in pl_keys if not (k in seen_pl or seen_pl.add(k))]

        # 3. Payload structure hash calculation if missing
        if not self.payload_structure_hash and self.payload_keys:
            key_repr = json.dumps(sorted(self.payload_keys))
            self.payload_structure_hash = hashlib.sha256(key_repr.encode("utf-8")).hexdigest()[:16]

        # 4. Headers fingerprint if raw headers were provided
        if self.headers is not None and not self.headers_fingerprint:
            if isinstance(self.headers, dict):
                h_keys = sorted([str(k).lower() for k in self.headers.keys()])
                self.headers_fingerprint = hashlib.sha256(json.dumps(h_keys).encode("utf-8")).hexdigest()[:16]

        # 5. Strictly discard raw values from object
        self.query_params = None
        self.raw_payload = None
        self.headers = None

        return self

class ApiRequestResponse(BaseModel):
    request_id: int
    session_id: str
    status: str = "RECORDED"
    sequence_number: Optional[int] = None

