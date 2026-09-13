/**
 * Group feature controller.
 *
 * Keeps group API calls and rendering in one feature boundary so new group
 * actions can be added here without modifying the application's global flow.
 */
import { state } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast } from '../ui/helpers.js';

let activeGroup = null;

/** Render the user's groups as full-width, semantic cards. */
export async function loadGroups() {
  const root = $('#groups-list');
  if (!root) return;
  root.innerHTML = '<div class="jarvis-loading">Загрузка…</div>';
  try {
    const groups = await request('/groups');
    root.innerHTML = groups.length
      ? groups.map(groupCard).join('')
      : '<div class="group-empty">Групп пока нет</div>';
  } catch (error) {
    root.innerHTML = `<div class="group-empty">${esc(error.message)}</div>`;
  }
}

/** Build one group list item; all user data is escaped before insertion. */
function groupCard(group) {
  const date = group.trip_start || 'Дата не задана';
  return `<button class="group-card" type="button" data-action="group-open" data-id="${Number(group.id)}">
    <span class="group-card-title">${esc(group.name)}</span>
    <span class="group-card-meta">${esc(date)}</span>
  </button>`;
}

/** Load and render a selected group, including its current discussion state. */
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

/** Keep group metadata rendering independent from message/proposal rendering. */
function renderGroupHeader() {
  $('#group-title').textContent = activeGroup.name;
  $('#group-date').value = activeGroup.trip_start || '';
  $('#group-members').innerHTML = (activeGroup.members || [])
    .map(member => `<span class="group-member">@${esc(member.username || member.user_id)}${member.role === 'owner' ? ' 👑' : ''}</span>`)
    .join('');
  const voting = $('#group-voting');
  if (voting) voting.textContent = activeGroup.is_voting_active ? 'Завершить голосование' : 'Начать голосование';
}

/** Switch screens without coupling the group feature to the global router. */
function showGroupScreen() {
  document.querySelectorAll('.screen').forEach(screen => screen.classList.remove('active'));
  $('#group')?.classList.add('active');
}

/** Refresh chat and route proposals in parallel. */
async function refreshGroup() {
  if (!activeGroup) return;
  const [messages, proposals] = await Promise.all([
    request(`/groups/${activeGroup.id}/messages`),
    request(`/groups/${activeGroup.id}/proposals`),
  ]);
  renderMessages(messages.messages || []);
  renderProposals(proposals.proposals || []);
}

/** Render chat messages with a small, readable Telegram-like layout. */
function renderMessages(messages) {
  const root = $('#group-chat');
  root.innerHTML = messages.length
    ? messages.map(message => `<div class="group-message"><div class="group-message-author">@${esc(message.username || message.author_id)}</div>${esc(message.text)}</div>`).join('')
    : '<div class="group-empty">Чат пуст</div>';
  root.scrollTop = root.scrollHeight;
}

/** Render route proposals and their current vote count. */
function renderProposals(proposals) {
  const root = $('#group-proposals');
  root.innerHTML = proposals.length
    ? proposals.map(item => `<div class="group-proposal"><span>${esc(item.name)} · ${Number(item.votes) || 0}</span><button type="button" class="btn-route" data-action="group-vote" data-place="${esc(item.place_id)}">👍</button></div>`).join('')
    : '<div class="group-empty">Нет предложений</div>';
}

/** Create a group; the trip date is set after creation from the dedicated date control. */
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

/** Save the group's trip date through the group API. */
export async function saveDate() {
  if (!activeGroup) return;
  const date = $('#group-date')?.value || null;
  try {
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

/** Send one chat message and refresh the message list. */
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

/** Add a place from the current feed to the active group's proposals. */
export async function proposePlace(placeId) {
  if (!activeGroup) return toast('Сначала откройте группу');
  try {
    await request(`/groups/${activeGroup.id}/proposals`, { method: 'POST', body: JSON.stringify({ place_id: String(placeId) }) });
    await refreshGroup();
    toast('Место предложено группе');
  } catch (error) {
    toast(error.message);
  }
}

/** Toggle the owner's group voting session. */
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
