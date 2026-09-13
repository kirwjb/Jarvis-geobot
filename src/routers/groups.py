from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from src.database.db import AsyncSessionLocal
from src.database.models import Group, GroupMember, GroupVote, User, Place

router = APIRouter(prefix='/api/groups', tags=['groups'])

class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    trip_start: str | None = None
class Username(BaseModel):
    username: str = Field(min_length=1, max_length=64)
class TextBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
class PlaceBody(BaseModel):
    place_id: str
class TripDate(BaseModel):
    trip_start: str | None = None

def uid(request: Request) -> int:
    return int(request.state.telegram_user_id)

async def is_member(session, group_id: int, user_id: int):
    return (await session.execute(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id))).scalar_one_or_none()

async def ensure_user(session, request: Request):
    user = (await session.execute(select(User).where(User.user_id == uid(request)))).scalar_one_or_none()
    if not user:
        session.add(User(user_id=uid(request), username=request.state.telegram_user.get('username')))
        await session.flush()

@router.post('')
async def create(body: GroupCreate, request: Request):
    async with AsyncSessionLocal() as session:
        await ensure_user(session, request)
        group = Group(name=body.name.strip(), owner_id=uid(request))
        session.add(group)
        await session.flush()
        if body.trip_start:
            await session.execute(text('UPDATE groups SET trip_start=:d WHERE id=:id'), {'d': body.trip_start, 'id': group.id})
        session.add(GroupMember(group_id=group.id, user_id=uid(request), role='owner'))
        await session.commit()
        return {'id': group.id, 'name': group.name, 'owner_id': group.owner_id, 'trip_start': body.trip_start}

@router.get('')
async def list_groups(request: Request):
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Group).join(GroupMember, GroupMember.group_id == Group.id).where(GroupMember.user_id == uid(request)).order_by(Group.id.desc()))).scalars().unique().all()
        out = []
        for group in rows:
            date = (await session.execute(text('SELECT trip_start FROM groups WHERE id=:id'), {'id': group.id})).scalar()
            out.append({'id': group.id, 'name': group.name, 'owner_id': group.owner_id, 'trip_start': date.isoformat() if date else None, 'is_voting_active': group.is_voting_active})
        return out

@router.get('/{group_id}')
async def detail(group_id: int, request: Request):
    async with AsyncSessionLocal() as session:
        if not await is_member(session, group_id, uid(request)): raise HTTPException(403, 'Not a group member')
        group = (await session.execute(select(Group).where(Group.id == group_id))).scalar_one_or_none()
        if not group: raise HTTPException(404, 'Group not found')
        date = (await session.execute(text('SELECT trip_start FROM groups WHERE id=:id'), {'id': group_id})).scalar()
        members = (await session.execute(select(User.user_id, User.username, GroupMember.role).join(GroupMember, GroupMember.user_id == User.user_id).where(GroupMember.group_id == group_id))).all()
        return {'id': group.id, 'name': group.name, 'owner_id': group.owner_id, 'trip_start': date.isoformat() if date else None, 'is_voting_active': group.is_voting_active, 'members': [{'user_id': a, 'username': b, 'role': c} for a, b, c in members]}

@router.patch('/{group_id}/date')
async def set_trip_date(group_id: int, body: TripDate, request: Request):
    """Save the trip start date; only the group owner may change it."""
    async with AsyncSessionLocal() as session:
        group = (await session.execute(select(Group).where(Group.id == group_id))).scalar_one_or_none()
        if not group: raise HTTPException(404, 'Group not found')
        if group.owner_id != uid(request): raise HTTPException(403, 'Only the owner can change the trip date')
        await session.execute(text('UPDATE groups SET trip_start=:d WHERE id=:id'), {'d': body.trip_start, 'id': group_id})
        await session.commit()
        return {'trip_start': body.trip_start}

@router.post('/{group_id}/invite')
async def invite(group_id: int, body: Username, request: Request):
    async with AsyncSessionLocal() as session:
        member = await is_member(session, group_id, uid(request))
        if not member or member.role not in ('owner', 'admin'): raise HTTPException(403, 'Only group managers can invite')
        username = body.username.strip().lstrip('@').lower()
        user = (await session.execute(select(User).where(func.lower(User.username) == username))).scalar_one_or_none()
        if not user: raise HTTPException(404, 'User is not registered in JARVIS')
        if await is_member(session, group_id, user.user_id): raise HTTPException(409, 'Already a member')
        return {'username': '@' + username, 'telegram_url': 'https://t.me/' + username, 'group_id': group_id}

@router.post('/{group_id}/join')
async def join(group_id: int, request: Request):
    async with AsyncSessionLocal() as session:
        if not (await session.execute(select(Group).where(Group.id == group_id))).scalar_one_or_none(): raise HTTPException(404, 'Group not found')
        if not await is_member(session, group_id, uid(request)):
            session.add(GroupMember(group_id=group_id, user_id=uid(request), role='member'))
            await session.commit()
        return {'joined': True}

@router.get('/{group_id}/messages')
async def messages(group_id: int, request: Request):
    async with AsyncSessionLocal() as session:
        if not await is_member(session, group_id, uid(request)): raise HTTPException(403, 'Not a group member')
        rows = (await session.execute(text('SELECT m.id,m.author_id,u.username,m.text,m.created_at FROM group_messages m JOIN users u ON u.user_id=m.author_id WHERE m.group_id=:g ORDER BY m.id ASC LIMIT 100'), {'g': group_id})).all()
        return {'messages': [dict(row._mapping) for row in rows]}

@router.post('/{group_id}/messages')
async def message(group_id: int, body: TextBody, request: Request):
    async with AsyncSessionLocal() as session:
        if not await is_member(session, group_id, uid(request)): raise HTTPException(403, 'Not a group member')
        await session.execute(text('INSERT INTO group_messages(group_id,author_id,text) VALUES(:g,:u,:t)'), {'g': group_id, 'u': uid(request), 't': body.text.strip()})
        await session.commit()
        return {'sent': True}

@router.post('/{group_id}/proposals')
async def proposal(group_id: int, body: PlaceBody, request: Request):
    async with AsyncSessionLocal() as session:
        if not await is_member(session, group_id, uid(request)): raise HTTPException(403, 'Not a group member')
        if not (await session.execute(select(Place).where(Place.place_id == body.place_id))).scalar_one_or_none(): raise HTTPException(404, 'Place not found')
        await session.execute(text('INSERT INTO group_proposals(group_id,author_id,place_id) VALUES(:g,:u,:p) ON CONFLICT (group_id,place_id) DO NOTHING'), {'g': group_id, 'u': uid(request), 'p': body.place_id})
        await session.commit()
        return {'proposed': True}

@router.get('/{group_id}/proposals')
async def proposals(group_id: int, request: Request):
    async with AsyncSessionLocal() as session:
        if not await is_member(session, group_id, uid(request)): raise HTTPException(403, 'Not a group member')
        rows = (await session.execute(text('SELECT p.place_id,pl.name,COUNT(v.id) votes FROM group_proposals p JOIN places pl ON pl.place_id=p.place_id LEFT JOIN group_votes v ON v.group_id=p.group_id AND v.place_id=p.place_id WHERE p.group_id=:g GROUP BY p.place_id,pl.name ORDER BY votes DESC,p.place_id'), {'g': group_id})).all()
        return {'proposals': [dict(row._mapping) for row in rows]}

@router.post('/{group_id}/voting')
async def voting(group_id: int, request: Request):
    async with AsyncSessionLocal() as session:
        member = await is_member(session, group_id, uid(request))
        if not member or member.role != 'owner': raise HTTPException(403, 'Only the owner controls voting')
        group = (await session.execute(select(Group).where(Group.id == group_id))).scalar_one()
        group.is_voting_active = not group.is_voting_active
        await session.commit()
        return {'is_voting_active': group.is_voting_active}

@router.post('/{group_id}/vote')
async def vote(group_id: int, body: PlaceBody, request: Request):
    async with AsyncSessionLocal() as session:
        if not await is_member(session, group_id, uid(request)): raise HTTPException(403, 'Not a group member')
        group = (await session.execute(select(Group).where(Group.id == group_id))).scalar_one()
        if not group.is_voting_active: raise HTTPException(409, 'Voting is not active')
        existing = (await session.execute(select(GroupVote).where(GroupVote.group_id == group_id, GroupVote.user_id == uid(request), GroupVote.place_id == body.place_id))).scalar_one_or_none()
        if existing:
            await session.delete(existing)
            voted = False
        else:
            session.add(GroupVote(group_id=group_id, user_id=uid(request), place_id=body.place_id))
            voted = True
        await session.commit()
        return {'voted': voted}
