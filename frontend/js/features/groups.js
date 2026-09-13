/**
 * Group feature controller.
 *
 * All group-specific API calls and rendering stay behind this boundary. The
 * global app only needs to dispatch group actions, making future controls
 * easy to add without growing a monolithic main.js.
 */
import { state } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast } from '../ui/helpers.js';

let activeGroup = null;

/** Render the user's groups as full-width semantic cards. */
export async function loadGroups() {
  const root = $('#groups-list');
  if (!root) return;
  root.innerHTML = '<div class="jarvis-loading">Загрузка…</div>';
  try {
    const groups = await request('/groups');
    root.innerHTML = groups.length ? groups.map(groupCard).join('') : '<div class="group-empty">Групп пока нет</div>';
  } catch (error) {
    root.innerHTML = `<div class="group-empty">${esc(error.message)}</div>`;
  }
}

function groupCard(group) {
  return `<button class="group-card" type="button" data-action="group-open" data-id="${Number(group.id)}"><span class="group-card-title">${esc(group.name)}</span><span class="group-card-meta">${esc(group.trip_start || 'Дата не задана')}</span></button>`;
}

/** Open a group and load its current members, proposals and chat. */
export async function openGroup(id) {
  try {
    activeGroup = await request(`/groups/${Number(id)}`);
    renderGroupHeader();
    showGroupScreen();
    await refreshGroup();
  } catch (error) {
    toast(error.message);
  }
}

function renderGroupHeader() {
  $('#group-title').textContent = activeGroup.name;
  $('#group-date').value = activeGroup.trip_start || '';
  $('#group-members').innerHTML = (activeGroup.members || []).map(member => `<span class="group-member">@${esc(member.username || member.user_id)}${member.role === 'owner' ? ' 👑' : ''}</span>`).join('');
  const voting = $('#group-voting');
  if (voting) voting.textContent = activeGroup.is_voting_active ? 'Завершить голосование' : 'Начать голосование';
}

function showGroupScreen() {
  document.querySelectorAll('.screen').forEach(screen => screen.classList.remove('active'));
  $('#group')?.classList.add('active');
}

/** Refresh independent group data in parallel. */
async function refreshGroup() {
  if (!activeGroup) return;
  const [messages, proposals] = await Promise.all([request(`/groups/${activeGroup.id}/messages`), request(`/groups/${activeGroup.id}/proposals`)]);
  renderMessages(messages.messages || []);
  renderProposals(proposals.proposals || []);
}

function renderMessages(messages) {
  const root = $('#group-chat');
  root.innerHTML = messages.length ? messages.map(message => `<div class="group-message"><div class="group-message-author">@${esc(message.username || message.author_id)}</div>${esc(message.text)}</div>`).join('') : '<div class="group-empty">Чат пуст</div>';
  root.scrollTop = root.scrollHeight;
}

function renderProposals(proposals) {
  const root = $('#group-proposals');
  root.innerHTML = proposals.length ? proposals.map(item => `<div class="group-proposal"><span>${esc(item.name)} · ${Number(item.votes) || 0}</span><button type="button" class="btn-route" data-action="group-vote" data-place="${esc(item.place_id)}">👍</button></div>`).join('') : '<div class="group-empty">Нет предложений</div>';
}

/** Create a group; its date can be assigned immediately after opening it. */
export async function createGroup() {
  const name = prompt('Название группы');
  if (!name?.trim()) return;
  try {
    const result = await request('/groups', { method: 'POST', body: JSON.stringify({ name: name.trim(), trip_start: null }) });
    await loadGroups();
    await openGroup(result.id);
  } catch (error) {
    toast(error.message);
  }
}

/** Persist the selected trip start date. */
export async function saveDate() {
  if (!activeGroup) return;
  try {
    const date = $('#group-date')?.value || null;
    await request(`/groups/${activeGroup.id}/date`, { method: 'PATCH', body: JSON.stringify({ trip_start: date }) });
    activeGroup.trip_start = date;
    toast('Дата сохранена');
  } catch (error) {
    toast(error.message);
  }
}

/** Invite a registered JARVIS user by Telegram username. */
export async function invite() {
  if (!activeGroup) return;
  const username = prompt('Username, например @example_123');
  if (!username?.trim()) return;
  try {
    const result = await request(`/groups/${activeGroup.id}/invite`, { method: 'POST', body: JSON.stringify({ username: username.trim() }) });
    toast(`Приглашение: ${result.telegram_url}`);
  } catch (error) {
    toast(error.message);
  }
}

/** Send a chat message and refresh the chat. */
export async function send() {
  if (!activeGroup) return;
  const input = $('#group-message');
  const text = input?.value.trim();
  if (!text) return;
  try {
    await request(`/groups/${activeGroup.id}/messages`, { method: 'POST', body: JSON.stringify({ text }) });
    input.value = '';
    await refreshGroup();
  } catch (error) {
    toast(error.message);
  }
}

/** Add a selected place to the active group's route proposals. */
export async function proposePlace(placeId) {
  if (!activeGroup) return toast('Сначала откройте группу');
  if (placeId) return submitProposal(placeId);

  if (!state.pois.length) return toast('Сначала откройте места');
  const picker = document.createElement('div');
  picker.className = 'jarvis-modal';
  picker.innerHTML = `<div class="jarvis-modal-card"><button class="jarvis-close" type="button" data-action="close-modal">×</button><h2>Предложить место</h2><div class="group-place-picker">${state.pois.map(place => `<button class="group-place-option" type="button" data-action="group-propose-place" data-place="${esc(place.id)}"><span>${esc(place.name)}</span><span>→</span></button>`).join('')}</div></div>`;
  document.body.appendChild(picker);
  picker.addEventListener('click', event => { if (event.target === picker) picker.remove(); });
}

/** Submit a proposal after the user selected a place in the picker. */
export async function submitProposal(placeId) {
  if (!activeGroup || !placeId) return;
  try {
    await request(`/groups/${activeGroup.id}/proposals`, { method: 'POST', body: JSON.stringify({ place_id: String(placeId) }) });
    document.querySelector('.jarvis-modal')?.remove();
    await refreshGroup();
    toast('Место предложено группе');
  } catch (error) {
    toast(error.message);
  }
}

/** Toggle the owner's voting session. */
export async function toggleVoting() {
  if (!activeGroup) return;
  try {
    const result = await request(`/groups/${activeGroup.id}/voting`, { method: 'POST' });
    activeGroup.is_voting_active = result.is_voting_active;
    renderGroupHeader();
    await refreshGroup();
  } catch (error) {
    toast(error.message);
  }
}

/** Cast or remove the current user's vote for a proposed place. */
export async function vote(placeId) {
  if (!activeGroup) return;
  try {
    await request(`/groups/${activeGroup.id}/vote`, { method: 'POST', body: JSON.stringify({ place_id: String(placeId) }) });
    await refreshGroup();
  } catch (error) {
    toast(error.message);
  }
}

export function currentGroupId() {
  return activeGroup?.id || null;
}
