from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

class AttackLog(BaseModel):
    ip_address: str
    timestamp: str
    attack_type: str
    location: str

attack_logs: List[AttackLog] = []

@app.post("/logs/")
def create_log(log: AttackLog):
    attack_logs.append(log)
    return {"message": "Log added successfully", "log": log}

@app.get("/logs/")
def read_logs():
    return attack_logs

@app.get("/")
def read_root():
    return {"message": "Welcome to the Server Attack Map API"}