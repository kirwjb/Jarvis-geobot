/**
 * Groups feature controller.
 *
 * This file coordinates state and user actions only. Network calls live in
 * api.js and DOM rendering lives in view.js, so new group buttons can be
 * implemented without expanding the global application controller.
 */
import { state } from '../core/state.js';
import { $, toast } from '../ui/helpers.js';
import { groupsApi } from './groups/api.js';
import { renderList, renderHeader, renderMessages, renderProposals, showGroupScreen } from './groups/view.js';

let activeGroup = null;

/** Load groups visible to the current Telegram user. */
export async function loadGroups() {
  const root = $('#groups-list');
  if (!root) return;
  root.innerHTML = '<div class="jarvis-loading">Загрузка…</div>';
  try { renderList(await groupsApi.list()); }
  catch (error) { root.innerHTML = `<div class="group-empty">${error.message}</div>`; }
}

/** Open one group and refresh all group-owned data. */
export async function openGroup(id) {
  try {
    activeGroup = await groupsApi.detail(id);
    renderHeader(activeGroup);
    showGroupScreen();
    await refreshGroup();
  } catch (error) { toast(error.message); }
}

/** Refresh independent group resources concurrently. */
async function refreshGroup() {
  if (!activeGroup) return;
  const [messages, proposals] = await Promise.all([groupsApi.messages(activeGroup.id), groupsApi.proposals(activeGroup.id)]);
  renderMessages(messages.messages || []);
  renderProposals(proposals.proposals || []);
}

/** Create a group, then open it immediately. */
export async function createGroup() {
  const name = prompt('Название группы');
  if (!name?.trim()) return;
  try { const result = await groupsApi.create(name); await loadGroups(); await openGroup(result.id); }
  catch (error) { toast(error.message); }
}

/** Save the group's trip start date. */
export async function saveDate() {
  if (!activeGroup) return;
  try {
    const date = $('#group-date')?.value || null;
    await groupsApi.setDate(activeGroup.id, date);
    activeGroup.trip_start = date;
    toast('Дата сохранена');
  } catch (error) { toast(error.message); }
}

/** Invite a registered JARVIS user by Telegram username. */
export async function invite() {
  if (!activeGroup) return;
  const username = prompt('Username, например @example_123');
  if (!username?.trim()) return;
  try { const result = await groupsApi.invite(activeGroup.id, username); toast(`Приглашение: ${result.telegram_url}`); }
  catch (error) { toast(error.message); }
}

/** Send a message to the current group's lightweight chat. */
export async function send() {
  if (!activeGroup) return;
  const input = $('#group-message');
  const text = input?.value.trim();
  if (!text) return;
  try { await groupsApi.sendMessage(activeGroup.id, text); input.value = ''; await refreshGroup(); }
  catch (error) { toast(error.message); }
}

/** Open a picker containing places from the current feed. */
export async function proposePlace() {
  if (!activeGroup) return toast('Сначала откройте группу');
  if (!state.pois.length) return toast('Сначала откройте места');
  const modal = document.createElement('div');
  modal.className = 'jarvis-modal';
  modal.innerHTML = `<div class="jarvis-modal-card"><button class="jarvis-close" type="button" data-action="close-modal">×</button><h2>Предложить место</h2><div class="group-place-picker">${state.pois.map(place => `<button class="group-place-option" type="button" data-action="group-propose-place" data-place="${place.id}"><span>${place.name}</span><span>→</span></button>`).join('')}</div></div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', event => { if (event.target === modal) modal.remove(); });
}

/** Submit one selected place as a group proposal. */
export async function submitProposal(placeId) {
  if (!activeGroup || !placeId) return;
  try { await groupsApi.propose(activeGroup.id, placeId); document.querySelector('.jarvis-modal')?.remove(); await refreshGroup(); toast('Место предложено группе'); }
  catch (error) { toast(error.message); }
}

/** Start or stop voting; only the backend-authorized owner can succeed. */
export async function toggleVoting() {
  if (!activeGroup) return;
  try { const result = await groupsApi.toggleVoting(activeGroup.id); activeGroup.is_voting_active = result.is_voting_active; renderHeader(activeGroup); await refreshGroup(); }
  catch (error) { toast(error.message); }
}

/** Toggle the current user's vote for a proposed place. */
export async function vote(placeId) {
  if (!activeGroup) return;
  try { await groupsApi.vote(activeGroup.id, placeId); await refreshGroup(); }
  catch (error) { toast(error.message); }
}
