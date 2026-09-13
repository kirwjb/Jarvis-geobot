/** Pure-ish DOM rendering helpers for the groups feature. */
import { $, esc } from '../../ui/helpers.js';

export function renderList(groups) {
  const root = $('#groups-list');
  if (!root) return;
  root.innerHTML = groups.length ? groups.map(group => `<button class="group-card" type="button" data-action="group-open" data-id="${Number(group.id)}"><span class="group-card-title">${esc(group.name)}</span><span class="group-card-meta">${esc(group.trip_start || 'Дата не задана')}</span></button>`).join('') : '<div class="group-empty">Групп пока нет</div>';
}

export function renderHeader(group) {
  $('#group-title').textContent = group.name;
  $('#group-date').value = group.trip_start || '';
  $('#group-members').innerHTML = (group.members || []).map(member => `<span class="group-member">@${esc(member.username || member.user_id)}${member.role === 'owner' ? ' 👑' : ''}</span>`).join('');
  const voting = $('#group-voting');
  if (voting) voting.textContent = group.is_voting_active ? 'Завершить голосование' : 'Начать голосование';
}

export function renderMessages(messages) {
  const root = $('#group-chat');
  root.innerHTML = messages.length ? messages.map(message => `<div class="group-message"><div class="group-message-author">@${esc(message.username || message.author_id)}</div>${esc(message.text)}</div>`).join('') : '<div class="group-empty">Чат пуст</div>';
  root.scrollTop = root.scrollHeight;
}

export function renderProposals(proposals) {
  const root = $('#group-proposals');
  root.innerHTML = proposals.length ? proposals.map(item => `<div class="group-proposal"><span>${esc(item.name)} · ${Number(item.votes) || 0}</span><button type="button" class="btn-route" data-action="group-vote" data-place="${esc(item.place_id)}">👍</button></div>`).join('') : '<div class="group-empty">Нет предложений</div>';
}

export function showGroupScreen() {
  document.querySelectorAll('.screen').forEach(screen => screen.classList.remove('active'));
  $('#group')?.classList.add('active');
}