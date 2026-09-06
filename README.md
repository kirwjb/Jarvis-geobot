# 🗺️ JARVIS GeoBot

> A Telegram travel assistant for discovering places, planning routes, checking weather, and exploring cities.

<p align="center">
  <img src="frontend/logo.svg" alt="JARVIS GeoBot" width="96">
</p>

<p align="center">
  <strong>Discover places. Plan routes. Explore more.</strong>
</p>

<p align="center">
  <code>v1.4126.060926</code> · <strong>Beta</strong>
</p>

---

## 📸 Screenshots

<!-- Add Mini App screenshots here -->

| Places | Weather | Route |
|:---:|:---:|:---:|
| `<!-- screenshot -->` | `<!-- screenshot -->` | `<!-- screenshot -->` |
| Add screenshot | Add screenshot | Add screenshot |

> Replace the placeholders above with screenshots when they are ready.

---

## ✨ Overview

**JARVIS GeoBot** is a Telegram bot and Mini App built for travel discovery and trip planning.

Instead of switching between several services, users can discover places, save interesting locations, build routes, check weather, and plan trips together — directly inside Telegram.

The project currently focuses primarily on **Belarus**, while the architecture is designed to support additional regions and external data sources.

### What users can do

- 🗺️ Explore interesting places in selected cities
- 🔎 Filter places by category
- 🖼️ View place information and available photos
- ❤️ Save places to Favorites
- 🧭 Build a personal route from selected locations
- 🌤️ Check weather for a selected city
- 👥 Plan trips collaboratively
- 🗳️ Vote for places during group planning
- 📍 Discover locations using OpenStreetMap data

---

## 🌐 Telegram Mini App

The **Telegram Mini App** is the main user-facing interface of JARVIS.

It is designed around a simple travel flow:

```text
Region → City → Interests → Places → Favorites / Route
```

### Main sections

| Section | Purpose |
|---|---|
| 🗺️ Regions | Choose a geographic region |
| 🏙️ Cities | Select a destination |
| 🏷️ Categories | Filter places by interests |
| 📍 Places | Discover points of interest |
| ❤️ Favorites | Save and revisit places |
| 🧭 Route | Manage selected locations |
| 🌤️ Weather | Check current weather |
| 👥 Groups | Plan trips together |

---

## 🗺️ Places

Places discovery is one of the core features of JARVIS.

Users select a region, city, and category to receive a feed of points of interest.

Each place card can include:

- Place name
- City
- Address
- Photo
- Favorite action
- Route action
- Detailed information

### Fast and incremental loading

The places feed uses **pagination** instead of loading the entire dataset at once.

Place photos are loaded independently from the main places request. This keeps the feed responsive even when a particular image is unavailable or takes longer to load.

```text
Places request
      │
      ▼
Render place cards
      │
      └──► Load missing photos asynchronously
```

### Data sources

Geographic information is primarily obtained from:

- **OpenStreetMap**
- **Overpass API**

Place images can be retrieved from **Wikimedia** services and cached by the backend.

---

## ❤️ Favorites

Interesting places can be saved to Favorites and accessed later.

Favorites are associated with the Telegram user and synchronized with the backend.

A place can be added or removed directly from its card, making it easy to build a personal collection of destinations.

---

## 🧭 Routes

JARVIS allows users to build a route from selected places.

Typical workflow:

1. Select a region
2. Select a city
3. Browse places
4. Add interesting locations to the route
5. Review the selected places
6. Build the route

Places can be added or removed directly from the places feed.

The route system is designed to turn a collection of interesting locations into a practical travel plan.

---

## 🌤️ Weather

JARVIS provides weather information for the selected city.

The Mini App can display:

- Temperature
- Weather description
- Humidity
- Wind speed
- Atmospheric pressure
- Cache status

Weather information can be refreshed directly from the Mini App.

---

## 👥 Group Trips

JARVIS also supports collaborative travel planning.

Groups can be used to build a shared trip with other users.

Group functionality includes:

- Creating groups
- Adding participants
- Managing members
- Selecting places together
- Voting for locations
- Approving places for a shared route
- Switching between individual and group planning

The group creator has extended management permissions.

---

## 🌍 Supported Geography

The current configuration includes the main regions of Belarus:

- 🇧🇾 Minsk Region
- 🇧🇾 Brest Region
- 🇧🇾 Vitebsk Region
- 🇧🇾 Gomel Region
- 🇧🇾 Grodno Region
- 🇧🇾 Mogilev Region

The project currently includes cities such as **Minsk, Brest, Grodno, Borisov, Soligorsk, Molodechno, Baranovichi, Pinsk, Kobrin, Vitebsk, Orsha, Polotsk, Novopolotsk, Gomel, Mozyr, Zhlobin, Rechitsa, Lida, Volkovysk, Smorgon, Mogilev, Bobruisk, Gorki, Osipovichi**, and others.

The city and region configuration can be expanded as the project grows.

---

## 🏗️ Architecture

JARVIS combines a Telegram bot, a FastAPI backend, a Telegram Mini App, persistent storage, caching, and external geographic services.

```text
                         ┌─────────────────────┐
                         │     Telegram User   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Telegram Mini App │
                         │      Frontend       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       FastAPI       │
                         │       REST API      │
                         └───────┬─────┬───────┘
                                 │     │
                    ┌────────────┘     └────────────┐
                    ▼                               ▼
             ┌─────────────┐                 ┌─────────────┐
             │ PostgreSQL  │                 │    Redis    │
             │   Database  │                 │ Cache/State │
             └─────────────┘                 └─────────────┘
                    │
                    ▼
             ┌─────────────────────┐
             │   External Services │
             │ OSM / Overpass      │
             │ Wikimedia           │
             └─────────────────────┘

                         ┌─────────────────────┐
                         │    Telegram Bot     │
                         │    AsyncTeleBot     │
                         └─────────────────────┘
```

---

## 🧰 Tech Stack

| Component | Technology |
|---|---|
| Backend | Python |
| API | FastAPI |
| Telegram Bot | pyTelegramBotAPI / AsyncTeleBot |
| ASGI Server | Uvicorn |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Cache / State | Redis |
| Geographic Data | OpenStreetMap / Overpass API |
| Place Images | Wikimedia |
| Frontend | HTML / CSS / JavaScript |
| Platform | Telegram Mini Apps |

---

## 📁 Project Structure

```text
Jarvis-geobot/
│
├── frontend/                  # Telegram Mini App
│   ├── css/
│   │   ├── interactions.css
│   │   ├── components.css
│   │   └── weather.css
│   │
│   ├── js/
│   │   ├── core/              # State, API and routing
│   │   ├── features/          # Travel, places, weather and routes
│   │   └── ui/                # Helpers, theme and localization
│   │
│   ├── index.html
│   └── logo.svg
│
├── src/
│   ├── database/              # Database models and sessions
│   ├── handlers/              # Telegram handlers
│   ├── middleware/            # Middleware and security
│   ├── routers/               # FastAPI endpoints
│   ├── services/              # External services
│   └── utils/                 # Utilities and localization
│
├── migrations/                # Alembic migrations
│
├── main.py                    # Telegram bot
├── main_combined.py           # Bot + FastAPI + Mini App
│
├── .env.example
├── alembic.ini
├── requirements.txt
├── package.json
└── LICENSE
```

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/kirwjb/Jarvis-geobot.git
cd Jarvis-geobot
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

#### Linux / macOS

```bash
source venv/bin/activate
```

#### Windows

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Create a `.env` file based on `.env.example`.

At minimum, configure the Telegram bot token:

```env
BOT_TOKEN=your_telegram_bot_token
```

Example PostgreSQL configuration:

```env
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jarvis_db
```

Example Redis configuration:

```env
REDIS_HOST=localhost
REDIS_PORT=6379
```

Additional configuration may include:

```env
DEFAULT_LANGUAGE=ru
DEFAULT_LIMIT=15
SUPER_ADMINS=123456789
```

> ⚠️ Never commit a real `.env` file, Telegram Bot Token, database password, or other secrets to GitHub.

---

## 🗄️ Database

JARVIS uses **PostgreSQL** for persistent application data.

After configuring the database, apply migrations:

```bash
alembic upgrade head
```

Database schema changes are managed with Alembic.

---

## 🔴 Redis

Redis is used for temporary and runtime data, including:

- User session state
- Caching
- Temporary application state
- Rate limiting
- Runtime locks
- Maintenance mode state

Example:

```env
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## ▶️ Running the Project

### Telegram Bot only

```bash
python main.py
```

### Full application

For the complete Telegram + Mini App environment:

```bash
python main_combined.py
```

This combines:

- Telegram Bot
- FastAPI
- Telegram Mini App
- REST API
- PostgreSQL
- Redis

The FastAPI server runs on the configured host and port, typically:

```text
http://localhost:8000
```

---

## 🔌 API

The backend exposes endpoints used by the Mini App.

Main endpoints include:

```text
/api/regions
/api/cities/{region_id}

/api/weather/{city}

/api/pois
/api/pois/query
/api/pois/{place_id}

/api/route/build

/api/favorites/toggle
/api/favorites/me

/api/auth/telegram

/api/health
```

The API separates the frontend from the database and external geographic services.

---

## 🗺️ Geographic Data

JARVIS uses **OpenStreetMap** and **Overpass API** for geographic data.

Overpass queries can be built around:

- City
- Region
- Category
- Geographic tags

Multiple Overpass endpoints can be configured to improve resilience.

Example:

```env
OVERPASS_URLS=https://example.com/api/interpreter,https://example2.com/api/interpreter
```

---

## 🖼️ Place Images

JARVIS can retrieve place images through Wikimedia services.

Images can be processed and cached by the backend to reduce repeated external requests.

Image retrieval is separated from the main places feed so that an unavailable image does not block the user interface.

---

## ⚡ Performance

The Mini App uses incremental loading to keep the interface responsive.

The places feed:

- Loads a limited number of places per page
- Uses pagination
- Avoids unnecessary requests
- Loads missing photos asynchronously
- Caches previously loaded pages
- Keeps navigation responsive

The backend also uses database queries and caching to reduce unnecessary external API requests.

---

## 🌐 Localization

The project includes a localization system with language resources for:

- 🇷🇺 Russian
- 🇬🇧 English
- 🇸🇦 Arabic
- 🇪🇸 Spanish
- 🇫🇷 French
- 🇩🇪 German

The Mini App also provides RU/BY interface localization where implemented.

---

## 🛡️ Security

JARVIS includes several application security mechanisms:

- Telegram authentication
- Administrator permission checks
- SUPERADMIN roles
- Rate limiting
- Redis-based state management
- Protected administrative actions
- Maintenance mode
- API error handling
- Separation of user and administrative functionality

Sensitive configuration is provided through environment variables rather than source code.

---

## 🧑‍💻 Development

The project follows a modular architecture.

Frontend functionality is organized into:

```text
core/
features/
ui/
```

Backend functionality is organized into:

```text
database/
handlers/
middleware/
routers/
services/
utils/
```

When adding a new feature, developers should preferably:

1. Keep frontend functionality inside the appropriate feature module.
2. Keep shared UI helpers inside `ui/`.
3. Keep application state inside the state module.
4. Add backend endpoints to the appropriate router.
5. Keep persistent data in PostgreSQL.
6. Use Redis for temporary state where appropriate.
7. Add localization for user-facing text.
8. Respect Telegram authentication and permission boundaries.
9. Reuse existing caching mechanisms where possible.

---

## 🧪 Beta Status

JARVIS GeoBot is currently in **Beta**.

The project is actively developed and tested. Interfaces, APIs, and individual features may continue to change between releases.

The current beta focuses on:

- Improving Mini App reliability
- Improving places discovery
- Improving image availability
- Refining navigation
- Improving route planning
- Improving performance
- Refining the overall user experience

### Current Release

**`v1.4126.060926 — Beta`**

---

## 🛣️ Roadmap

Planned development directions include:

- [ ] Expand geographic coverage
- [ ] Improve place search and filtering
- [ ] Improve photo coverage and fallback sources
- [ ] Improve route optimization
- [ ] Expand group trip functionality
- [ ] Improve Telegram Mini App UX
- [ ] Expand localization
- [ ] Add additional geographic data sources
- [ ] Improve caching and performance
- [ ] Improve API reliability
- [ ] Add more travel-oriented features

---

## 📜 License

See [`LICENSE`](LICENSE) for license information.

---

## 🤖 JARVIS GeoBot

**Discover places. Plan routes. Explore more.**

Built as a Telegram-first travel experience with a focus on geographic discovery, route planning, and simple trip organization.
