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
    logger.info("New user registered for username: %s", account.username)
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


"""

# AWS
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# GitHub Token
GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz

# Slack Token
SLACK_BOT_TOKEN=xoxb-123456789012-123456789012-abcdefghijklmnopqrstuvwx

# Stripe
STRIPE_SECRET_KEY=sk_test_51NExampleSecretKey123456789

# Google API
GOOGLE_API_KEY=AIzaSyDUMMYExampleKey1234567890

# JWT Secret
JWT_SECRET=my_super_secret_jwt_signing_key_12345

# Database URLs
DATABASE_URL=postgres://admin:SuperSecretPassword@db.example.com:5432/appdb
MONGO_URI=mongodb://root:password123@mongo.example.com:27017/testdb

# SSH Private Key
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAlwAAAAdzc2gtcn
NhAAAAAwEAAQAAAIEA1FakeKeyExampleOnlyDontUseInProduction1234567890
-----END OPENSSH PRIVATE KEY-----

# PEM Certificate
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCExampleFakePrivateKey123456789
-----END PRIVATE KEY-----

# Twilio
TWILIO_AUTH_TOKEN=1234567890abcdef1234567890abcdef

# SendGrid
SENDGRID_API_KEY=SG.fake-example-api-key-1234567890

# Generic Passwords
password=SuperSecret123!
admin_password=P@ssw0rd!
redis_password=redisStrongPass123

# Kubernetes Secret YAML
apiVersion: v1
kind: Secret
metadata:
  name: example-secret
type: Opaque
data:
  password: U3VwZXJTZWNyZXQxMjMh

# .npmrc
//registry.npmjs.org/:_authToken=npm_fakeToken1234567890

# Docker Auth
DOCKER_AUTH_CONFIG={"auths":{"https://index.docker.io/v1/":{"auth":"ZHVtbXk6cGFzc3dvcmQ="}}}


"""
