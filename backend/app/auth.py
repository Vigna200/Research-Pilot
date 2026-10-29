"""Local password + OTP authentication. Production SMS delivery requires a configured provider."""
from datetime import datetime, timedelta, timezone
import base64, hashlib, hmac, json, secrets
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from .config import settings
from .database import OtpChallengeRecord, UserRecord, engine
from .schemas import AuthChallenge, AuthToken, LoginRequest, OtpVerifyRequest, SignUpRequest

def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.urlsafe_b64encode(salt).decode() + "." + base64.urlsafe_b64encode(digest).decode()

def _password_matches(password: str, saved: str) -> bool:
    salt_text, _ = saved.split(".", 1)
    return hmac.compare_digest(_hash_password(password, base64.urlsafe_b64decode(salt_text)), saved)

def _token(user: UserRecord) -> AuthToken:
    payload = {"sub": user.id, "email": user.email, "exp": int((datetime.now(timezone.utc) + timedelta(hours=12)).timestamp())}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(settings.auth_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return AuthToken(access_token=f"{encoded}.{signature}", user={"id": user.id, "name": user.full_name, "email": user.email})

def _challenge(user: UserRecord) -> AuthChallenge:
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge_id = secrets.token_hex(16)
    with Session(engine) as db:
        db.add(OtpChallengeRecord(id=challenge_id, user_id=user.id, code_hash=hashlib.sha256(code.encode()).hexdigest(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expiry_minutes), consumed=False))
        db.commit()
    delivery = "development" if settings.otp_development_mode else "sms_provider_not_configured"
    return AuthChallenge(challenge_id=challenge_id, delivery=delivery, expires_in_seconds=settings.otp_expiry_minutes * 60, development_code=code if settings.otp_development_mode else None)

def sign_up(request: SignUpRequest) -> AuthChallenge:
    with Session(engine) as db:
        if db.query(UserRecord).filter(UserRecord.email == request.email.lower()).first(): raise HTTPException(409, "An account with this email already exists")
        user = UserRecord(id=secrets.token_hex(16), full_name=request.full_name, email=request.email.lower(), phone_number=request.phone_number, password_hash=_hash_password(request.password), verified=False, created_at=datetime.now(timezone.utc))
        db.add(user); db.commit(); db.refresh(user)
    return _challenge(user)

def login(request: LoginRequest) -> AuthChallenge:
    with Session(engine) as db:
        user = db.query(UserRecord).filter(UserRecord.email == request.email.lower()).first()
        if not user or not _password_matches(request.password, user.password_hash): raise HTTPException(401, "Invalid email or password")
    return _challenge(user)

def verify_otp(request: OtpVerifyRequest) -> AuthToken:
    with Session(engine) as db:
        challenge = db.get(OtpChallengeRecord, request.challenge_id)
        expiry = challenge.expires_at if challenge and challenge.expires_at.tzinfo else (challenge.expires_at.replace(tzinfo=timezone.utc) if challenge else None)
        if not challenge or challenge.consumed or expiry < datetime.now(timezone.utc): raise HTTPException(400, "OTP is expired or invalid")
        if not hmac.compare_digest(challenge.code_hash, hashlib.sha256(request.code.encode()).hexdigest()): raise HTTPException(400, "Incorrect OTP")
        challenge.consumed = True
        user = db.get(UserRecord, challenge.user_id); user.verified = True
        db.commit(); return _token(user)

def current_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401, "Sign in is required")
    try:
        encoded, signature = authorization.removeprefix("Bearer ").rsplit(".", 1)
        expected = hmac.new(settings.auth_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature): raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if payload["exp"] < int(datetime.now(timezone.utc).timestamp()): raise ValueError
        return {"id": payload["sub"], "email": payload["email"]}
    except (ValueError, KeyError, json.JSONDecodeError): raise HTTPException(401, "Invalid or expired session")
