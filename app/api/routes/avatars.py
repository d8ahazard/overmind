from fastapi import APIRouter, HTTPException

router = APIRouter()

PIXEL_AVATARS = [
    "pixel_1.svg",
    "pixel_2.svg",
    "pixel_3.svg",
    "pixel_4.svg",
]


@router.get("/pixel")
def list_pixel_avatars() -> list[dict]:
    return [{"id": name, "path": f"/public/avatars/{name}"} for name in PIXEL_AVATARS]


@router.post("/generate")
def generate_avatar(payload: dict) -> dict:
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    # Placeholder: wire to image generation provider later.
    return {"status": "queued", "name": name}
