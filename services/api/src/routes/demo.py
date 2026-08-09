from fastapi import APIRouter

from ..store import store

router = APIRouter()


@router.post("/demo/reset")
def reset_demo():
    store.reset()
    return {"ok": True}
