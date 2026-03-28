import secrets
from datetime import datetime, timezone
import os
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, select, func
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from fastapi.middleware.cors import CORSMiddleware

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def utcnow():
    return datetime.now(timezone.utc)


def make_token():
    return secrets.token_urlsafe(32)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    user_token = Column(String(128), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    robots = relationship("Robot", back_populates="owner")
    commands = relationship("Command", back_populates="user")


class Robot(Base):
    __tablename__ = "robots"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    robot_token = Column(String(128), unique=True, nullable=False, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    owner = relationship("User", back_populates="robots")
    commands = relationship("Command", back_populates="robot")


class Command(Base):
    __tablename__ = "commands"
    id = Column(Integer, primary_key=True, index=True)
    robot_id = Column(Integer, ForeignKey("robots.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    command_text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=True)

    robot = relationship("Robot", back_populates="commands")
    user = relationship("User", back_populates="commands")


class UserCreate(BaseModel):
    name: str


class RobotCreate(BaseModel):
    name: str


class ClaimRobotRequest(BaseModel):
    robot_token: str


class SendCommandRequest(BaseModel):
    robot_id: int
    command_text: str


class AckCommandRequest(BaseModel):
    command_id: int


def require_user(db: Session, token: str | None):
    if not token:
        raise HTTPException(status_code=401, detail="Missing X-User-Token")
    user = db.execute(select(User).where(User.user_token == token)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user token")
    return user


def require_robot(db: Session, token: str | None):
    if not token:
        raise HTTPException(status_code=401, detail="Missing X-Robot-Token")
    robot = db.execute(select(Robot).where(Robot.robot_token == token)).scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=401, detail="Invalid robot token")
    return robot


Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "robot api running"}


@app.get("/health/db")
def db_health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"db": "ok"}


@app.post("/register/user")
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = User(name=payload.name, user_token=make_token())
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user_id": user.id, "name": user.name, "user_token": user.user_token}


@app.post("/register/robot")
def register_robot(payload: RobotCreate, db: Session = Depends(get_db)):
    robot = Robot(name=payload.name, robot_token=make_token())
    db.add(robot)
    db.commit()
    db.refresh(robot)
    return {"robot_id": robot.id, "name": robot.name, "robot_token": robot.robot_token}


@app.post("/user/claim-robot")
def claim_robot(payload: ClaimRobotRequest, x_user_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = require_user(db, x_user_token)
    robot = db.execute(select(Robot).where(Robot.robot_token == payload.robot_token)).scalar_one_or_none()

    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    if robot.owner_user_id is not None and robot.owner_user_id != user.id:
        raise HTTPException(status_code=409, detail="Robot already owned by another user")

    robot.owner_user_id = user.id
    db.commit()
    db.refresh(robot)

    return {"message": "robot claimed", "robot_id": robot.id, "owner_user_id": robot.owner_user_id}


@app.post("/user/send-command")
def send_command(payload: SendCommandRequest, x_user_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = require_user(db, x_user_token)
    robot = db.get(Robot, payload.robot_id)

    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    if robot.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this robot")

    cmd = Command(robot_id=robot.id, user_id=user.id, command_text=payload.command_text, status="pending")
    db.add(cmd)
    db.commit()
    db.refresh(cmd)

    return {"message": "command queued", "command_id": cmd.id, "status": cmd.status}


@app.get("/robot/poll")
def robot_poll(x_robot_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    robot = require_robot(db, x_robot_token)

    cmd = (
        db.execute(
            select(Command)
            .where(Command.robot_id == robot.id, Command.status == "pending")
            .order_by(Command.created_at.asc())
        )
        .scalars()
        .first()
    )

    if not cmd:
        return {"command": None}

    return {"command": {"command_id": cmd.id, "command_text": cmd.command_text, "status": cmd.status}}


@app.post("/robot/received")
def robot_received(payload: AckCommandRequest, x_robot_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    robot = require_robot(db, x_robot_token)
    cmd = db.get(Command, payload.command_id)

    if not cmd or cmd.robot_id != robot.id:
        raise HTTPException(status_code=404, detail="Command not found")

    cmd.status = "received"
    cmd.received_at = utcnow()
    db.commit()
    db.refresh(cmd)

    return {"message": "command marked received", "command_id": cmd.id, "status": cmd.status}


@app.get("/user/my-robots")
def my_robots(x_user_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = require_user(db, x_user_token)
    robots = db.execute(select(Robot).where(Robot.owner_user_id == user.id)).scalars().all()
    return [{"robot_id": r.id, "name": r.name} for r in robots]


@app.get("/robots/available")
def available_robots(db: Session = Depends(get_db)):
    count = db.query(func.count(Robot.id)).filter(Robot.owner_user_id.is_(None)).scalar()
    return {"available_robots": count}
    
@app.post("/user/assign-free-robot")
def assign_free_robot(
    x_user_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not x_user_token:
        raise HTTPException(status_code=401, detail="Missing X-User-Token")

    user = db.execute(
        select(User).where(User.user_token == x_user_token)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid user token")

    existing_robot = db.execute(
        select(Robot).where(Robot.owner_user_id == user.id).order_by(Robot.id.asc())
    ).scalar_one_or_none()

    if existing_robot:
        return {
            "message": "user already has a robot",
            "robot_id": existing_robot.id,
            "robot_name": existing_robot.name,
            "owner_user_id": existing_robot.owner_user_id,
            "robot_token": existing_robot.robot_token,
        }

    robot = db.execute(
        select(Robot)
        .where(Robot.owner_user_id.is_(None))
        .order_by(Robot.id.asc())
    ).scalar_one_or_none()

    if not robot:
        raise HTTPException(status_code=404, detail="No free robot available")

    robot.owner_user_id = user.id
    db.commit()
    db.refresh(robot)

    return {
        "message": "free robot assigned",
        "robot_id": robot.id,
        "robot_name": robot.name,
        "owner_user_id": robot.owner_user_id,
        "robot_token": robot.robot_token,
    }

@app.delete("/admin/delete-all-robots")
def delete_all_robots(db: Session = Depends(get_db)):
    db.query(Command).delete()
    db.query(Robot).delete()
    db.commit()
    return {"message": "all robots and related commands deleted"}

@app.post("/user/release-robot")
def release_robot(
    robot_id: int,
    x_user_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = require_user(db, x_user_token)

    robot = db.get(Robot, robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")

    if robot.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this robot")

    db.query(Command).filter(Command.robot_id == robot.id).delete()
    robot.owner_user_id = None
    db.commit()
    db.refresh(robot)

    return {
        "message": "robot released",
        "robot_id": robot.id,
        "owner_user_id": robot.owner_user_id,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
    )
