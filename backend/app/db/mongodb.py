import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pymongo import MongoClient, ASCENDING as ASC
from app.config import settings

logger = logging.getLogger("mongodb_service")

class MongoResumeStore:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.parse_cache_col = None
        self.in_memory_store: Dict[str, Dict[str, Any]] = {}
        self.in_memory_parse_cache: Dict[str, Dict[str, Any]] = {}
        self._init_connection()

    def _init_connection(self):
        try:
            self.client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=1500)
            self.client.admin.command('ping')
            self.db = self.client[settings.MONGO_DB_NAME]
            self.collection = self.db["scanned_resumes"]
            self.parse_cache_col = self.db["parse_cache"]
            
            # Create Indexes
            self.collection.create_index("unique_fingerprint", unique=True)
            self.parse_cache_col.create_index([("kind", ASC), ("hash", ASC), ("prompt_version", ASC), ("model_id", ASC)], unique=True)
            logger.info("Successfully connected to live MongoDB server with parse_cache.")
        except Exception as e:
            logger.warning(f"MongoDB server connection fallback to in-memory store: {e}")
            self.client = None
            self.collection = None
            self.parse_cache_col = None

    @staticmethod
    def generate_candidate_fingerprint(
        name: str = "",
        email: str = "",
        phone: str = "",
        degree: str = "",
        raw_text_sample: str = ""
    ) -> str:
        """Generates a unique deterministic SHA-256 fingerprint hash for candidate identity."""
        norm_name = name.strip().lower() if name else ""
        norm_email = email.strip().lower() if email else ""
        norm_phone = "".join(filter(str.isdigit, phone)) if phone else ""
        norm_degree = degree.strip().lower() if degree else ""
        
        if not norm_name and not norm_email and not norm_phone:
            identity_str = raw_text_sample[:300].strip().lower()
        else:
            identity_str = f"{norm_name}|{norm_email}|{norm_phone}|{norm_degree}"
            
        return hashlib.sha256(identity_str.encode('utf-8')).hexdigest()

    def get_cached_parse(self, cache_key: Dict[str, str]) -> Optional[Dict[str, Any]]:
        key_str = f"{cache_key['kind']}:{cache_key['hash']}:{cache_key['prompt_version']}:{cache_key['model_id']}"
        if self.parse_cache_col is not None:
            try:
                return self.parse_cache_col.find_one(cache_key)
            except Exception:
                pass
        return self.in_memory_parse_cache.get(key_str)

    def save_cached_parse(self, cache_key: Dict[str, str], profile_data: Dict[str, Any]):
        key_str = f"{cache_key['kind']}:{cache_key['hash']}:{cache_key['prompt_version']}:{cache_key['model_id']}"
        doc = {**cache_key, "profile": profile_data, "created_at": datetime.utcnow().isoformat()}
        if self.parse_cache_col is not None:
            try:
                self.parse_cache_col.update_one(cache_key, {"$set": doc}, upsert=True)
                return
            except Exception:
                pass
        self.in_memory_parse_cache[key_str] = doc

    def save_or_update_resume(
        self,
        candidate_id: str,
        filename: str,
        raw_text_scrubbed: str,
        parsed_profile: Dict[str, Any],
        fingerprint: str
    ) -> Dict[str, Any]:
        """Saves new resume or updates existing candidate record if fingerprint matches."""
        now = datetime.utcnow().isoformat()
        
        existing_doc = None
        if self.collection is not None:
            try:
                existing_doc = self.collection.find_one({"unique_fingerprint": fingerprint})
            except Exception as e:
                logger.warning(f"MongoDB query error: {e}")
        else:
            existing_doc = self.in_memory_store.get(fingerprint)

        if existing_doc:
            new_version = existing_doc.get("version", 1) + 1
            update_payload = {
                "latest_candidate_id": candidate_id,
                "latest_filename": filename,
                "raw_text_scrubbed": raw_text_scrubbed,
                "parsed_profile": parsed_profile,
                "version": new_version,
                "is_updated_resume": True,
                "updated_at": now
            }
            
            if self.collection is not None:
                self.collection.update_one(
                    {"unique_fingerprint": fingerprint},
                    {"$set": update_payload, "$push": {"filename_history": filename}}
                )
            else:
                existing_doc.update(update_payload)
                existing_doc.setdefault("filename_history", []).append(filename)
                self.in_memory_store[fingerprint] = existing_doc
                
            logger.info(f"[UPSERT] Updated existing candidate (fingerprint: {fingerprint[:8]}..., version: {new_version}).")
            return {
                "fingerprint": fingerprint,
                "version": new_version,
                "is_updated_resume": True,
                "message": f"Updated existing candidate profile (v{new_version})"
            }
        else:
            new_doc = {
                "candidate_id": candidate_id,
                "unique_fingerprint": fingerprint,
                "original_filename": filename,
                "filename_history": [filename],
                "raw_text_scrubbed": raw_text_scrubbed,
                "parsed_profile": parsed_profile,
                "version": 1,
                "is_updated_resume": False,
                "created_at": now,
                "updated_at": now
            }
            
            if self.collection is not None:
                try:
                    self.collection.insert_one(new_doc)
                except Exception as e:
                    logger.warning(f"MongoDB insert error: {e}")
            else:
                self.in_memory_store[fingerprint] = new_doc
                
            logger.info(f"[INSERT] Registered new candidate profile (fingerprint: {fingerprint[:8]}...).")
            return {
                "fingerprint": fingerprint,
                "version": 1,
                "is_updated_resume": False,
                "message": "New candidate profile registered"
            }

mongo_store = MongoResumeStore()
