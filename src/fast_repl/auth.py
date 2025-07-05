# TODO: use prisma python with pg??

# # app/auth.py
# import os
# from fastapi import HTTPException, Security
# from fastapi.security.api_key import APIKeyHeader
# from sqlalchemy import create_engine, Table, Column, String, MetaData, select

# API_KEY = os.getenv("API_KEY") or ""
# engine = create_engine("sqlite:///data/keys.db")
# metadata = MetaData()
# keys = Table("keys", metadata, Column("key", String, primary_key=True))
# metadata.create_all(engine)

# def seed_key():
#     with engine.begin() as conn:
#         if not conn.execute(select(keys)).first():
#             conn.execute(keys.insert().values(key=API_KEY))

# api_key_header = APIKeyHeader(name="Authorization")

# async def require_key(auth: str = Security(api_key_header)):
#     token = auth.removeprefix("Bearer ").strip()
#     with engine.connect() as conn:
#         row = conn.execute(select(keys).where(keys.c.key == token)).first()
#     if not row:
#         raise HTTPException(401, "Invalid API key")
#     return token
