from fastapi import APIRouter, Depends, HTTPException
from schemas.community import FeatureRequestCreate, ReviewCreate
from services.auth_service import AuthenticatedUser, get_authenticated_user
from services.community_service import CommunityService

router = APIRouter()
service = CommunityService()

@router.get("/summary")
def summary(user: AuthenticatedUser = Depends(get_authenticated_user)):
    return service.summary(user_id=user.id)

@router.post("/reviews")
def review(request: ReviewCreate, user: AuthenticatedUser = Depends(get_authenticated_user)):
    try:
        saved = service.submit_review(
            user_id=user.id, rating=request.rating, title=request.title,
            body=request.body, publish_consent=request.publish_consent,
            publish_name=request.publish_name, display_name=request.display_name,
        )
        return {"saved": True, "review_id": saved["id"], "published": bool(saved.get("publish_consent"))}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to save the review.") from exc

@router.post("/features")
def feature(request: FeatureRequestCreate, user: AuthenticatedUser = Depends(get_authenticated_user)):
    try:
        return {"saved": True, "feature_request": service.submit_feature(
            user_id=user.id, title=request.title, description=request.description
        )}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to save the feature request.") from exc

@router.post("/features/{feature_request_id}/vote")
def vote(feature_request_id: str, user: AuthenticatedUser = Depends(get_authenticated_user)):
    try:
        return service.toggle_vote(user_id=user.id, feature_request_id=feature_request_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to update the vote.") from exc
