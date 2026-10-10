# 🗺️ JARVIS GeoBot

> A Telegram travel assistant for discovering places, planning routes, checking weather, and exploring cities.

<p align="center">
  <img src="frontend/logo.svg" alt="JARVIS GeoBot" width="160">
</p>

<p align="center">
  <img src="frontend/logo_art.svg" alt="JARVIS ASCII Art" width="600">
</p>

<p align="center">
  <strong>Discover places. Plan routes. Explore more.</strong>
</p>

<p align="center">
  <code>v2.25.10102026</code> · <strong>Stable Release</strong>
</p>

---

## 📸 Screenshots

<p align="center">
  <img src="https://github.com/user-attachments/assets/e542e4f3-277a-41f3-96fb-7468a1670159" alt="Places" width="220">
  <img src="https://github.com/user-attachments/assets/da32c2aa-8e8e-4346-8cfe-2c2f9aaa6e86" alt="Weather" width="220">
  <img src="https://github.com/user-attachments/assets/2cb92f73-3cb6-4ae1-81cd-af87aab910f2" alt="Route" width="220">
</p>

<p align="center"><strong>Places</strong>　　<strong>Weather</strong>　　<strong>Route</strong></p>

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
├── jarvis.py                  # Main entry point and CLI
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
venv\\Scripts\\activate
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

### Full application

For the complete Telegram + Mini App environment:

```bash
./jarvis -r
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

---

## 🛡️ Security & Role-Based Access Control (RBAC)

JARVIS features a strict three-tier **Role-Based Access Control (RBAC)** architecture:

```text
USER (1) < ADMIN (2) < SUPERADMIN (3)
```

- **👑 SUPERADMIN (Supreme & Immutable)**:
  - Configured strictly via environment variables (`BOT_OWNER_ID` or `SUPERADMIN_ID` or `SUPER_ADMINS`).
  - Supreme, unalterable platform privileges across all sub-systems.
  - Exclusive access to host CLI administration (`./Jarvis -a`) and in-chat governance (`/promote`, `/demote`, `/maintenance`).
  - Immune from moderation actions (cannot be banned, muted, or demoted by anyone).
- **🛡️ ADMIN (Moderation & Operations)**:
  - Granted administrative privileges exclusively by a Superadmin.
  - In-chat moderation privileges (`/ban`, `/unban`, `/mute`, `/unmute`, `/user`, `/broadcast`).
  - Bypasses global maintenance mode alongside Superadmins.
  - Enforced target hierarchy: Admins cannot ban or mute fellow Admins or Superadmins.
- **👤 USER (Standard Citizens)**:
  - Standard Telegram bot conversation and Telegram Mini App travel discovery.
  - Governed by rate limiting and global maintenance mode restrictions.

---

## 🛠️ Administrative Orchestration & CLI Control Center

Administration is split cleanly between in-chat Telegram moderation and direct host machine orchestration via `./Jarvis -a`:

### In-Chat Telegram Moderation & Governance

| Command | Scope | Functionality |
|---|---|---|
| `/ban <id \| @username> [reason]` | ADMIN & SUPERADMIN | Restrict user access across Telegram bot and Mini App |
| `/unban <id \| @username>` | ADMIN & SUPERADMIN | Reinstate full user access privileges |
| `/mute <id \| @username> [reason]` | ADMIN & SUPERADMIN | Suppress conversational messaging privileges |
| `/unmute <id \| @username>` | ADMIN & SUPERADMIN | Restore conversational messaging privileges |
| `/user <id \| @username>` | ADMIN & SUPERADMIN | Inspect user dossier: role, registration date, route count, and flags |
| `/broadcast <text>` | ADMIN & SUPERADMIN | Safe batch dispatch to active users (respects Telegram TPS limits) |
| `/promote <id \| @username>` | SUPERADMIN ONLY | Elevate standard user to `ADMIN` role |
| `/demote <id \| @username>` | SUPERADMIN ONLY | Strip administrative privileges back to `USER` role |
| `/maintenance [on\|off]` | SUPERADMIN ONLY | Toggle global platform maintenance flag in Redis |

### Terminal Admin Control Center (`./Jarvis -a` in `src/cli/admin.py`)

Restricted exclusively to the platform Superadmin with direct host access:

```bash
# Interactive Control Center
./Jarvis -a

# Operational & Database Metrics
./Jarvis -a stats                     # System metrics: registered users, POIs, routes, cache
./Jarvis -a db-vacuum                 # Execute PostgreSQL VACUUM ANALYZE optimizer
./Jarvis -a migrations                # Audit pending Alembic schema revisions
./Jarvis -a redis-metrics             # Inspect cache hit/miss ratio, memory footprint, keyspace
./Jarvis -a latency                   # Measure round-trip latency to Postgres, Redis & OSM mirrors

# User Directory & Role Governance
./Jarvis -a users                     # Paginated user browser with role filtering & flag toggling
./Jarvis -a ban <id|user> [reason]    # Ban user across DB and Redis cache
./Jarvis -a unban <id|user>           # Unban user
./Jarvis -a mute <id|user> [reason]   # Mute user
./Jarvis -a unmute <id|user>          # Unmute user
./Jarvis -a promote <id|user>         # Elevate user to ADMIN
./Jarvis -a demote <id|user>          # Demote user to USER
./Jarvis -a clear-city <name>         # Purge cached OSM places, photos, and weather for a city

# Bourgeois & Aristocratic Satirical Easter Eggs
./Jarvis -a guillotine <user>         # Satirical French Revolution decree of exile
./Jarvis -a salon                     # Rococo tea & champagne high-society telemetry dossier
```

---

## 🌤️ Weather Service Guard & Localization (RU / BY)

The weather subsystem in `src/services/weather_service.py` includes proactive input validation and localization:

- **Missing City Guard**: Catches unselected city scenarios (`None`, `"none"`, `"null"`, `"undefined"`, or empty strings) without querying external APIs or raising unhandled HTTP 500 exceptions.
- **Bilingual Guidance (RU / BY)**:
  - 🇷🇺 **Russian (RU)**: *"Сначала выберите город в разделе «Путешествия»."*
  - 🇧🇾 **Belarusian (BY)**: *"Спачатку выберыце горад у раздзеле «Падарожжы»."*
- **Mini App Empty State**: Automatically presents the dedicated empty weather view with a single-tap *"Выбрать город"* / *"Выбраць горад"* navigation button.

---

## 🧑‍💻 Development

The project follows a modular architecture:

```text
frontend/
  core/
  features/
  ui/

src/
  cli/
  database/
  handlers/
  middleware/
  routers/
  services/
  utils/
```

---

## 🚀 Release Status

JARVIS GeoBot is in a **Stable** production release.

### Current Release

**`v2.25.10102026 — Stable`**

#### What's New in v2.25.10102026:
- 👑 **Three-Tier RBAC Hierarchy**: Complete `USER < ADMIN < SUPERADMIN` permission model with immutable Superadmin authority.
- 🛠️ **Administrative CLI Center**: Vacuum analyzer, Alembic migration audit, Redis cache telemetry, round-trip latency diagnostics, and paginated user directory.
- 🤖 **In-Chat Moderation Suite**: Full set of moderation (`/ban`, `/unban`, `/mute`, `/unmute`, `/user`, `/broadcast`) and governance (`/promote`, `/demote`, `/maintenance`) handlers.
- 🌤️ **Weather Service Guard**: Catches missing city payloads gracefully and guides users in Russian (RU) and Belarusian (BY).
- ⚖️ **Satirical Easter Eggs**: Revolutionary guillotine exile decrees and Rococo high-society telemetry salon.
- 🧪 **Test Suite Expansion**: Comprehensive unit tests validating all RBAC privilege boundaries, middleware filters, and weather guards.

---

## 🛣️ Roadmap

Planned development directions include:

- [ ] Expand geographic coverage
- [ ] Improve place search and filtering
- [ ] Improve photo coverage and fallback sources
- [ ] Improve route optimization
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
