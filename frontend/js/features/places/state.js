/** Runtime-only state owned by the places feature. */
export const placesState = {
  pageSize: 8,
  page: 0,
  hasNext: false,
  loading: false,
  queryKey: '',
  search: '',
  shuffleSeed: '',
  cache: new Map(),
  photoLoading: new Set(),
};

/** Generate a random alphanumeric seed for session-consistent reproducible shuffling. */
export function generateShuffleSeed() {
  return Math.random().toString(36).substring(2, 10);
}

/** Build a stable key so changing city, categories, search or shuffle invalidates page data. */
export function buildPlacesQueryKey(state) {
  return JSON.stringify({
    region: state.region,
    city: state.city,
    tags: [...state.tags].sort(),
    search: placesState.search || '',
    shuffleSeed: placesState.shuffleSeed || '',
  });
}

/** Reset transient pagination state when a new places query starts. */
export function resetPlacesState() {
  placesState.page = 0;
  placesState.hasNext = false;
  placesState.loading = false;
  placesState.queryKey = '';
  placesState.search = '';
  placesState.shuffleSeed = '';
  placesState.cache.clear();
}
