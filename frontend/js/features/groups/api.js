/** Group API boundary. UI code never builds group endpoint URLs directly. */
import { request } from '../../core/api.js';

export const groupsApi = {
  list: () => request('/groups'),
  detail: id => request(`/groups/${Number(id)}`),
  create: name => request('/groups', { method: 'POST', body: JSON.stringify({ name: name.trim(), trip_start: null }) }),
  setDate: (id, trip_start) => request(`/groups/${Number(id)}/date`, { method: 'PATCH', body: JSON.stringify({ trip_start }) }),
  invite: (id, username) => request(`/groups/${Number(id)}/invite`, { method: 'POST', body: JSON.stringify({ username: username.trim() }) }),
  messages: id => request(`/groups/${Number(id)}/messages`),
  sendMessage: (id, text) => request(`/groups/${Number(id)}/messages`, { method: 'POST', body: JSON.stringify({ text }) }),
  proposals: id => request(`/groups/${Number(id)}/proposals`),
  propose: (id, place_id) => request(`/groups/${Number(id)}/proposals`, { method: 'POST', body: JSON.stringify({ place_id: String(place_id) }) }),
  toggleVoting: id => request(`/groups/${Number(id)}/voting`, { method: 'POST' }),
  vote: (id, place_id) => request(`/groups/${Number(id)}/vote`, { method: 'POST', body: JSON.stringify({ place_id: String(place_id) }) }),
};