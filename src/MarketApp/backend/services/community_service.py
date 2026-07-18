from __future__ import annotations
from typing import Any
from services.supabase_service import SupabaseService

class CommunityService:
    def __init__(self) -> None:
        self.client = SupabaseService().client

    @staticmethod
    def clean(value: str) -> str:
        return " ".join(str(value or "").strip().split())

    def submit_review(self, *, user_id: str, rating: int, title: str, body: str,
                      publish_consent: bool, publish_name: bool,
                      display_name: str | None) -> dict[str, Any]:
        payload = {
            "user_id": user_id,
            "rating": int(rating),
            "title": self.clean(title),
            "body": str(body or "").strip(),
            "publish_consent": bool(publish_consent),
            "publish_name": bool(publish_consent and publish_name),
            "display_name": self.clean(display_name or "") or None
                if publish_consent and publish_name else None,
        }
        result = self.client.table("community_reviews").upsert(
            payload, on_conflict="user_id"
        ).execute()
        if not result.data:
            raise RuntimeError("Unable to save review.")
        return result.data[0]

    def submit_feature(self, *, user_id: str, title: str, description: str) -> dict[str, Any]:
        result = self.client.table("feature_requests").insert({
            "user_id": user_id,
            "title": self.clean(title),
            "description": str(description or "").strip(),
            "status": "submitted",
        }).execute()
        if not result.data:
            raise RuntimeError("Unable to save feature request.")
        return result.data[0]

    def toggle_vote(self, *, user_id: str, feature_request_id: str) -> dict[str, bool]:
        existing = self.client.table("feature_votes").select("id").eq(
            "user_id", user_id
        ).eq("feature_request_id", feature_request_id).limit(1).execute()
        if existing.data:
            self.client.table("feature_votes").delete().eq(
                "id", existing.data[0]["id"]
            ).execute()
            return {"voted": False}
        self.client.table("feature_votes").insert({
            "user_id": user_id,
            "feature_request_id": feature_request_id,
        }).execute()
        return {"voted": True}

    def summary(self, *, user_id: str) -> dict[str, Any]:
        published = self.client.table("community_reviews").select(
            "id,rating,title,body,publish_name,display_name,created_at"
        ).eq("publish_consent", True).order("created_at", desc=True).limit(12).execute().data or []
        all_ratings = self.client.table("community_reviews").select("rating").eq(
            "publish_consent", True
        ).execute().data or []
        avg = sum(float(x.get("rating") or 0) for x in all_ratings) / len(all_ratings) if all_ratings else 0

        features = self.client.table("feature_requests").select(
            "id,title,description,status,created_at"
        ).order("created_at", desc=True).limit(100).execute().data or []
        votes = self.client.table("feature_votes").select(
            "feature_request_id,user_id"
        ).execute().data or []
        counts, mine = {}, set()
        for vote in votes:
            fid = str(vote.get("feature_request_id"))
            counts[fid] = counts.get(fid, 0) + 1
            if str(vote.get("user_id")) == str(user_id):
                mine.add(fid)
        enriched = [{**f, "votes": counts.get(str(f["id"]), 0),
                     "user_voted": str(f["id"]) in mine} for f in features]
        enriched.sort(key=lambda x: (-int(x["votes"]), str(x.get("created_at") or "")))

        roadmap = self.client.table("roadmap_items").select(
            "id,title,description,status,sort_order"
        ).order("sort_order").execute().data or []

        return {
            "rating_average": round(avg, 2),
            "published_review_count": len(all_ratings),
            "reviews": [{**r, "author": r.get("display_name") if r.get("publish_name") and r.get("display_name") else "Anonymous investor"} for r in published],
            "feature_requests": enriched,
            "roadmap": roadmap,
        }
