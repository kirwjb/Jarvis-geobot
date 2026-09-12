from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from src.database.db import AsyncSessionLocal
from src.database.models import Group, GroupMember, GroupVote, User, Place

router=APIRouter(prefix='/api/groups',tags=['groups'])
class GroupCreate(BaseModel): name:str=Field(min_length=1,max_length=120); trip_start:str|None=None
class Username(BaseModel): username:str=Field(min_length=1,max_length=64)
class TextBody(BaseModel): text:str=Field(min_length=1,max_length=2000)
class PlaceBody(BaseModel): place_id:str

def uid(request): return int(request.state.telegram_user_id)
async def is_member(s,g,u): return (await s.execute(select(GroupMember).where(GroupMember.group_id==g,GroupMember.user_id==u))).scalar_one_or_none()
async def ensure_user(s,request):
    u=(await s.execute(select(User).where(User.user_id==uid(request)))).scalar_one_or_none()
    if not u:s.add(User(user_id=uid(request),username=request.state.telegram_user.get('username')));await s.flush()

@router.post('')
async def create(body:GroupCreate,request:Request):
    async with AsyncSessionLocal() as s:
        await ensure_user(s,request); g=Group(name=body.name.strip(),owner_id=uid(request));s.add(g);await s.flush()
        if body.trip_start: await s.execute(text('UPDATE groups SET trip_start=:d WHERE id=:id'),{'d':body.trip_start,'id':g.id})
        s.add(GroupMember(group_id=g.id,user_id=uid(request),role='owner'));await s.commit();return {'id':g.id,'name':g.name,'owner_id':g.owner_id,'trip_start':body.trip_start}

@router.get('')
async def list_groups(request:Request):
    async with AsyncSessionLocal() as s:
        rows=(await s.execute(select(Group).join(GroupMember,GroupMember.group_id==Group.id).where(GroupMember.user_id==uid(request)).order_by(Group.id.desc()))).scalars().unique().all()
        out=[]
        for g in rows:
            d=(await s.execute(text('SELECT trip_start FROM groups WHERE id=:id'),{'id':g.id})).scalar()
            out.append({'id':g.id,'name':g.name,'owner_id':g.owner_id,'trip_start':d.isoformat() if d else None,'is_voting_active':g.is_voting_active})
        return out

@router.get('/{group_id}')
async def detail(group_id:int,request:Request):
    async with AsyncSessionLocal() as s:
        if not await is_member(s,group_id,uid(request)):raise HTTPException(403,'Not a group member')
        g=(await s.execute(select(Group).where(Group.id==group_id))).scalar_one_or_none()
        if not g:raise HTTPException(404,'Group not found')
        d=(await s.execute(text('SELECT trip_start FROM groups WHERE id=:id'),{'id':group_id})).scalar()
        ms=(await s.execute(select(User.user_id,User.username,GroupMember.role).join(GroupMember,GroupMember.user_id==User.user_id).where(GroupMember.group_id==group_id))).all()
        return {'id':g.id,'name':g.name,'owner_id':g.owner_id,'trip_start':d.isoformat() if d else None,'is_voting_active':g.is_voting_active,'members':[{'user_id':a,'username':b,'role':c} for a,b,c in ms]}

@router.post('/{group_id}/invite')
async def invite(group_id:int,body:Username,request:Request):
    async with AsyncSessionLocal() as s:
        m=await is_member(s,group_id,uid(request));
        if not m or m.role not in ('owner','admin'):raise HTTPException(403,'Only group managers can invite')
        username=body.username.strip().lstrip('@').lower();u=(await s.execute(select(User).where(func.lower(User.username)==username))).scalar_one_or_none()
        if not u:raise HTTPException(404,'User is not registered in JARVIS')
        if await is_member(s,group_id,u.user_id):raise HTTPException(409,'Already a member')
        return {'username':'@'+username,'telegram_url':'https://t.me/'+username,'group_id':group_id}

@router.post('/{group_id}/join')
async def join(group_id:int,request:Request):
    async with AsyncSessionLocal() as s:
        if not (await s.execute(select(Group).where(Group.id==group_id))).scalar_one_or_none():raise HTTPException(404,'Group not found')
        if not await is_member(s,group_id,uid(request)):s.add(GroupMember(group_id=group_id,user_id=uid(request),role='member'));await s.commit()
        return {'joined':True}

@router.get('/{group_id}/messages')
async def messages(group_id:int,request:Request):
    async with AsyncSessionLocal() as s:
        if not await is_member(s,group_id,uid(request)):raise HTTPException(403,'Not a group member')
        rows=(await s.execute(text('SELECT m.id,m.author_id,u.username,m.text,m.created_at FROM group_messages m JOIN users u ON u.user_id=m.author_id WHERE m.group_id=:g ORDER BY m.id ASC LIMIT 100'),{'g':group_id})).all()
        return {'messages':[dict(r._mapping) for r in rows]}

@router.post('/{group_id}/messages')
async def message(group_id:int,body:TextBody,request:Request):
    async with AsyncSessionLocal() as s:
        if not await is_member(s,group_id,uid(request)):raise HTTPException(403,'Not a group member')
        await s.execute(text('INSERT INTO group_messages(group_id,author_id,text) VALUES(:g,:u,:t)'),{'g':group_id,'u':uid(request),'t':body.text.strip()});await s.commit();return {'sent':True}

@router.post('/{group_id}/proposals')
async def proposal(group_id:int,body:PlaceBody,request:Request):
    async with AsyncSessionLocal() as s:
        if not await is_member(s,group_id,uid(request)):raise HTTPException(403,'Not a group member')
        if not (await s.execute(select(Place).where(Place.place_id==body.place_id))).scalar_one_or_none():raise HTTPException(404,'Place not found')
        await s.execute(text('INSERT INTO group_proposals(group_id,author_id,place_id) VALUES(:g,:u,:p) ON CONFLICT (group_id,place_id) DO NOTHING'),{'g':group_id,'u':uid(request),'p':body.place_id});await s.commit();return {'proposed':True}

@router.get('/{group_id}/proposals')
async def proposals(group_id:int,request:Request):
    async with AsyncSessionLocal() as s:
        if not await is_member(s,group_id,uid(request)):raise HTTPException(403,'Not a group member')
        rows=(await s.execute(text('SELECT p.place_id,pl.name,COUNT(v.id) votes FROM group_proposals p JOIN places pl ON pl.place_id=p.place_id LEFT JOIN group_votes v ON v.group_id=p.group_id AND v.place_id=p.place_id WHERE p.group_id=:g GROUP BY p.place_id,pl.name ORDER BY votes DESC,p.place_id'),{'g':group_id})).all()
        return {'proposals':[dict(r._mapping) for r in rows]}

@router.post('/{group_id}/voting')
async def voting(group_id:int,request:Request):
    async with AsyncSessionLocal() as s:
        m=await is_member(s,group_id,uid(request));
        if not m or m.role!='owner':raise HTTPException(403,'Only the owner controls voting')
        g=(await s.execute(select(Group).where(Group.id==group_id))).scalar_one();g.is_voting_active=not g.is_voting_active;await s.commit();return {'is_voting_active':g.is_voting_active}

@router.post('/{group_id}/vote')
async def vote(group_id:int,body:PlaceBody,request:Request):
    async with AsyncSessionLocal() as s:
        if not await is_member(s,group_id,uid(request)):raise HTTPException(403,'Not a group member')
        g=(await s.execute(select(Group).where(Group.id==group_id))).scalar_one()
        if not g.is_voting_active:raise HTTPException(409,'Voting is not active')
        exists=(await s.execute(select(GroupVote).where(GroupVote.group_id==group_id,GroupVote.user_id==uid(request),GroupVote.place_id==body.place_id))).scalar_one_or_none()
        if exists:await s.delete(exists);v=False
        else:s.add(GroupVote(group_id=group_id,user_id=uid(request),place_id=body.place_id));v=True
        await s.commit();return {'voted':v}
