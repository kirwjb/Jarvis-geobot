/** Runtime-only state owned by the places feature. */
export const placesState = {
  pageSize: 8,
  page: 0,
  hasNext: false,
  loading: false,
  queryKey: '',
  cache: new Map(),
  photoLoading: new Set(),
};

/** Build a stable key so changing city or categories invalidates page data. */
export function buildPlacesQueryKey(state) {
  return JSON.stringify({ region: state.region, city: state.city, tags: [...state.tags].sort() });
}

/** Reset transient pagination state when a new places query starts. */
export function resetPlacesState() {
  placesState.page = 0;
  placesState.hasNext = false;
  placesState.loading = false;
  placesState.queryKey = '';
  placesState.cache.clear();
}
