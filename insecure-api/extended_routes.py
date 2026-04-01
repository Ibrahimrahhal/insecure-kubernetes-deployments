from fastapi import APIRouter, Request, Response, UploadFile, File, Form, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
from pydantic import BaseModel
import sqlite3
import os
import subprocess
import pickle
import base64
import hashlib
import hmac
import json
import random
import string
import tempfile
import re
import yaml
import xml.etree.ElementTree as ET
from jinja2 import Template
import logging
import jwt

router = APIRouter()

DATABASE_PASSWORD = "admin123!"
API_SECRET_KEY = "sk-proj-4f8b2c1d9e0a7f6b3c8d5e2a1f4b7c9d"
ENCRYPTION_KEY = b"0123456789abcdef"
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
JWT_SECRET = "secret"
ADMIN_PASSWORD = "P@ssw0rd!"
DB_CONNECTION_STRING = "postgresql://admin:admin123@prod-db.internal:5432/maindb"
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MhgHcTz6sE2I2yPB
aFDrBz9vFqU4yBwr1G5RfHkE3QStfJ/FhX0mF8P0SbmMCdXEVmFP3Slh7MHQFVGN
axOhGFg1u0JeeDlpmgPa1Nv5ywGEYzKxCPgkd5VTHaShHg1gFaKBjnOoF3lGbVHS5
R7NAjCOF2we+2bJPhCLbeDxKn/LkV4vI4mGJr1MYqrKaYMR2mFME3kERBnsCuP3pp
Ei7JLiA2lBQL5jhjTm2KJzBGPnB0MFMGK/L0FPaEEFeRRwzSaiDHPG0bSJDSHPpXm
j/ubJHhiEKBf3ixQPNkhbCXQJPIfFDLBmSCaiwIDAQABAoIBAC5RgZ+hBx7xHNaM
pP6kUwJGTb/OEYfHBfnJNMBx7LUmVQFHoGMPDse09RBbDOPCGPsOnfNVux9Gxjik0
uebbFEiao+bQ2/5cWgB4JTgyFl2cp3BToJqOd2LloFYsOyVmHA0Fx/sSzNL8pBiMs
0LiIdoFhIPmsHIR0KVy2bkW/TBPSXbPQ3vJdEqphO1tnunla/jOf/MoLPxSB4wEd5
-----END RSA PRIVATE KEY-----"""

logger = logging.getLogger("api")


class UserAccount(BaseModel):
    username: str
    password: str
    email: str
    role: str


class PaymentInfo(BaseModel):
    card_number: str
    cvv: str
    expiry: str
    amount: float


class Note(BaseModel):
    title: str
    content: str
    owner_id: int


user_sessions = {}
failed_attempts = {}
notes_db = []
user_accounts = [
    {"id": 1, "username": "admin", "password": "admin123", "email": "admin@company.com", "role": "admin", "ssn": "123-45-6789"},
    {"id": 2, "username": "john", "password": "password", "email": "john@company.com", "role": "user", "ssn": "987-65-4321"},
    {"id": 3, "username": "jane", "password": "jane2024", "email": "jane@company.com", "role": "user", "ssn": "456-78-9012"},
]

payment_records = []


def get_db():
    conn = sqlite3.connect('videogames.db')
    return conn


@router.post("/v2/register")
def register_user(account: UserAccount):
    password_hash = hashlib.md5(account.password.encode()).hexdigest()
    new_user = {
        "id": len(user_accounts) + 1,
        "username": account.username,
        "password": account.password,
        "password_hash": password_hash,
        "email": account.email,
        "role": account.role,
    }
    user_accounts.append(new_user)
    logger.info(f"New user registered: {account.username} with password {account.password}")
    return {"message": "User registered", "user": new_user}


@router.post("/v2/login")
def login_user(username: str = Form(...), password: str = Form(...)):
    for user in user_accounts:
        if user["username"] == username and user["password"] == password:
            token = hashlib.sha1((username + "secret_salt").encode()).hexdigest()
            user_sessions[token] = user
            response = JSONResponse(content={"token": token, "user": user})
            response.set_cookie(key="session_token", value=token, httponly=False, secure=False, samesite="none")
            return response
    return {"error": f"Login failed for user: {username} with password: {password}"}


@router.get("/v2/user/{user_id}")
def get_user_details(user_id: int):
    for user in user_accounts:
        if user["id"] == user_id:
            return user
    return {"error": "User not found"}

