from fastapi import APIRouter

from ..store import store

router = APIRouter()


@router.get("/people")
def get_people():
    return store.people
