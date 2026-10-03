import hashlib
import hmac
import re
from typing import List, Dict, Any, Tuple
from datasketch import MinHash, MinHashLSH
from app.schemas import DuplicateGroup, DedupConfig

def get_5gram_shingles(text: str) -> set:
    words = re.findall(r"\w+", text.lower())
    if len(words) < 5:
        return set()
    return {" ".join(words[i:i + 5]) for i in range(len(words) - 4)}

def compute_minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for s in get_5gram_shingles(text):
        m.update(s.encode("utf-8"))
    return m

class DedupService:
    @staticmethod
    def generate_salted_hash(val: str, salt: str = "tcs_resurrection_salt") -> str:
        if not val:
            return ""
        norm_val = "".join(filter(str.isalnum, val.lower()))
        return hmac.new(salt.encode("utf-8"), norm_val.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def detect_duplicates(
        cls,
        candidates_data: List[Dict[str, Any]],
        config: Optional[DedupConfig] = None
    ) -> List[DuplicateGroup]:
        
        cfg = config or DedupConfig()
        duplicate_groups: List[DuplicateGroup] = []
        
        # 1. Exact Duplicate detection (Normalized Text SHA-256)
        text_hash_map: Dict[str, List[str]] = {}
        for item in candidates_data:
            cid = item["candidate_id"]
            text = item.get("sanitized_text", "")
            norm_text = re.sub(r"\s+", " ", text.lower().strip())
            h = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()
            text_hash_map.setdefault(h, []).append(cid)

        exact_grp_idx = 1
        for h, cids in text_hash_map.items():
            if len(cids) > 1:
                duplicate_groups.append(DuplicateGroup(
                    group_id=f"DUP-EXACT-{exact_grp_idx}",
                    kind="EXACT",
                    similarity=1.0,
                    members=cids,
                    canonical=cids[0],
                    detail=f"Identical sanitized text hash among {len(cids)} resumes."
                ))
                exact_grp_idx += 1

        # 2. Same Applicant detection (Email/Phone salted HMAC match)
        email_hash_map: Dict[str, List[str]] = {}
        for item in candidates_data:
            cid = item["candidate_id"]
            email = item.get("extracted_email", "")
            if email:
                eh = cls.generate_salted_hash(email)
                email_hash_map.setdefault(eh, []).append(cid)

        same_app_idx = 1
        for eh, cids in email_hash_map.items():
            if len(cids) > 1:
                duplicate_groups.append(DuplicateGroup(
                    group_id=f"DUP-SAME-{same_app_idx}",
                    kind="SAME_APPLICANT",
                    similarity=1.0,
                    members=cids,
                    canonical=cids[0],
                    detail=f"Same applicant contact identity detected."
                ))
                same_app_idx += 1

        # 3. Near-Duplicate detection (MinHash LSH Jaccard >= 0.85)
        lsh = MinHashLSH(threshold=cfg.near_dup_jaccard, num_perm=128)
        minhashes: Dict[str, MinHash] = {}

        for item in candidates_data:
            cid = item["candidate_id"]
            text = item.get("sanitized_text", "")
            mh = compute_minhash(text)
            minhashes[cid] = mh
            try:
                lsh.insert(cid, mh)
            except Exception:
                pass

        near_dup_idx = 1
        processed_pairs = set()
        for cid, mh in minhashes.items():
            results = lsh.query(mh)
            if len(results) > 1:
                sorted_cluster = sorted(results)
                cluster_key = tuple(sorted_cluster)
                if cluster_key not in processed_pairs:
                    processed_pairs.add(cluster_key)
                    # Check if already caught by EXACT
                    if not any(set(sorted_cluster).issubset(set(g.members)) for g in duplicate_groups if g.kind == "EXACT"):
                        jaccard_sim = mh.jaccard(minhashes[sorted_cluster[1]]) if len(sorted_cluster) > 1 else 0.90
                        duplicate_groups.append(DuplicateGroup(
                            group_id=f"DUP-NEAR-{near_dup_idx}",
                            kind="NEAR_DUPLICATE",
                            similarity=round(jaccard_sim, 2),
                            members=sorted_cluster,
                            canonical=sorted_cluster[0],
                            detail=f"Near-duplicate text structure (Jaccard similarity >= {cfg.near_dup_jaccard})."
                        ))
                        near_dup_idx += 1

        return duplicate_groups

    @classmethod
    def detect_project_plagiarism(
        cls,
        parsed_candidates: List[Any],
        config: Optional[DedupConfig] = None
    ) -> List[DuplicateGroup]:
        
        cfg = config or DedupConfig()
        plagiarism_groups: List[DuplicateGroup] = []
        
        # Collect candidate projects
        candidate_projects: List[Tuple[str, str]] = []  # (candidate_id, project_desc)
        for cand in parsed_candidates:
            cid = cand.candidate_id
            for proj in getattr(cand, "projects", []):
                desc = proj.description if hasattr(proj, "description") else str(proj)
                if len(desc.split()) >= cfg.project_min_words:
                    candidate_projects.append((cid, desc))

        if len(candidate_projects) < 2:
            return plagiarism_groups

        # MinHash compare projects between different candidates
        proj_idx = 1
        for i in range(len(candidate_projects)):
            cid1, desc1 = candidate_projects[i]
            mh1 = compute_minhash(desc1)
            for j in range(i + 1, len(candidate_projects)):
                cid2, desc2 = candidate_projects[j]
                if cid1 == cid2:
                    continue
                mh2 = compute_minhash(desc2)
                sim = mh1.jaccard(mh2)
                if sim >= cfg.project_plagiarism_jaccard:
                    plagiarism_groups.append(DuplicateGroup(
                        group_id=f"DUP-PROJ-{proj_idx}",
                        kind="SHARED_PROJECT_TEXT",
                        similarity=round(sim, 2),
                        members=[cid1, cid2],
                        canonical=None,
                        detail=f"Shared project text detected between candidates (Jaccard similarity {sim*100:.1f}%)."
                    ))
                    proj_idx += 1

        return plagiarism_groups
