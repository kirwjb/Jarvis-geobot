# JARVIS Geo-App Frontend

The frontend is a lightweight, dependency-free vanilla JavaScript Telegram Mini App structured by modular domains.

## Directory Structure

```text
frontend/
├── index.html                 # Semantic UI shell; screens and containers
├── favicon.svg                # Favicon
├── logo.svg                   # Logo
├── style.css                  # Forwarding alias (@import css/style.css)
├── css/
│   ├── style.css              # Color tokens, dark/light themes, typography, layout
│   ├── components.css         # UI cards, buttons, modals, toasts, pagination, feed tools
│   ├── interactions.css       # Active states, touch feedback
│   └── weather.css            # Weather shell & metric blocks
└── js/
    ├── main.js                # App bootstrapping & composition root
    ├── app/
    │   └── events.js          # Centralized event delegation layer
    ├── core/
    │   ├── api.js             # HTTP request helper with error handling
    │   ├── router.js          # Screen navigation & Telegram WebApp BackButton
    │   └── state.js           # Shared state & localStorage persistence
    ├── ui/
    │   ├── helpers.js         # DOM utilities, toast, haptics, HTML escaping
    │   ├── language.js        # RU/BY i18n dictionaries & language toggling
    │   └── theme.js           # Theme controller & Telegram WebApp style sync
    └── features/
        ├── travel.js          # Region, city, and tag selection
        ├── places.js          # POI feed controller, free search & random shuffling
        ├── places/
        │   ├── pagination.js  # POI feed page loading & cache
        │   ├── photos.js      # Image tag rendering & Wikimedia proxy
        │   ├── state.js       # Search query, shuffle seed & pagination state
        │   └── view.js        # POI card templates & feed rendering
        ├── favorites.js       # Favorites loading, toggling, and paginated screen
        ├── route.js           # Route building, point management & FAB state
        └── weather.js         # City weather view & cache
```

## Key Rules

1. **Markup Only in HTML**: `index.html` contains no inline event handlers (`onclick`, etc.).
2. **Centralized Event Delegation**: All interactive elements use `data-action="..."` and are handled via `js/app/events.js`.
3. **Domain Ownership**: Domain logic is contained in its respective feature file (`favorites.js`, `route.js`, `travel.js`, `places.js`, `weather.js`).
4. **Resilient Offline/TMA Support**: Runs both inside Telegram Mini App and standalone browsers.
