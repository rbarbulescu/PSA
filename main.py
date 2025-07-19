from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.hash import bcrypt
import os

# Database Setup
DATABASE_URL = "mysql+mysqlconnector://user:password@127.0.0.1:3306/dogbnb"
engine = create_engine(DATABASE_URL)
Base = declarative_base()
DBSession = sessionmaker(bind=engine)

# FastAPI Setup
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(100), nullable=False)

    def verify_password(self, password: str) -> bool:
        return bcrypt.verify(password, self.password_hash)

class Listing(Base):
    __tablename__ = "listings"
    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    description = Column(Text)
    client_id = Column(Integer, ForeignKey("users.id"))

Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = DBSession()
    try:
        yield db
    finally:
        db.close()

# Routes
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register-form", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register-form", response_class=HTMLResponse)
def register(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing = db.query(User).filter_by(username=username).first()
    if existing:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already taken"})
    
    user = User(username=username, password_hash=bcrypt.hash(password))
    db.add(user)
    db.commit()
    return RedirectResponse(url="/login-form", status_code=302)

@app.get("/login-form", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login-form", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=username).first()
    if not user or not user.verify_password(password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    return RedirectResponse(url="/listings", status_code=302)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)

@app.get("/listings", response_class=HTMLResponse)
def show_listings(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    username = request.session.get("username")
    if not user_id:
        return RedirectResponse(url="/login-form", status_code=302)

    listings = db.query(Listing).filter_by(client_id=user_id).all()
    return templates.TemplateResponse("listings.html", {"request": request, "listings": listings, "username": username})

@app.post("/add-listing", response_class=HTMLResponse)
def add_listing(request: Request, title: str = Form(...), description: str = Form(...), db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login-form", status_code=302)

    listing = Listing(title=title, description=description, client_id=user_id)
    db.add(listing)
    db.commit()
    return RedirectResponse(url="/listings", status_code=302)
