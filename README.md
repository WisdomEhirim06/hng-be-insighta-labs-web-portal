# Insighta Labs+ Web Portal

A premium, secure web-based interface for the Insighta Labs+ Profile Intelligence System. This portal provides non-technical users (Analysts) and administrators with a powerful dashboard to explore, search, and manage global profile data.

## System Architecture

The Insighta Labs+ platform is a unified ecosystem consisting of three primary components:
- **Backend API**: The central intelligence hub handling data collection, storage, and natural language processing.
- **Web Portal (This Repo)**: A FastAPI-based proxy and templating engine providing a glassmorphism-styled UI.
- **CLI Tool**: A terminal interface for power users and engineers.

The Web Portal acts as a secure client to the Backend API, communicating over HTTPS with strict versioning (`X-API-Version: 1`) and session-based authentication.

## Authentication Flow

The portal implements a secure **GitHub OAuth 2.0** flow with a specialized redirect mechanism:

1. **Initiation**: User clicks "Continue with GitHub".
2. **State Generation**: The portal generates a cryptographically secure nonce and encodes it into a `state` parameter along with a callback identifier: `web:<token_receive_url>:<nonce>`.
3. **GitHub Authorization**: User authenticates on GitHub.
4. **Backend Processing**: GitHub redirects to the central Backend API. The backend parses the `state`, completes the OAuth exchange, and identifies that the request originated from the web portal.
5. **Token Delivery**: The backend redirects the user back to the portal's `/auth/tokens` endpoint, passing the JWT Access and Refresh tokens.
6. **Session Establishment**: The portal receives the tokens and stores them in **HTTP-only, Secure, SameSite=Lax** cookies.

## Token Handling Approach

Security is prioritized through strict token management:
- **Access Tokens**: Short-lived (3 minutes) JWTs used for all API requests.
- **Refresh Tokens**: Used to obtain new access tokens (expiry: 5 minutes).
- **HTTP-Only Cookies**: Tokens are never accessible to client-side JavaScript, effectively neutralizing XSS attacks.
- **Automatic Cleanup**: Logging out deletes all session cookies and invalidates the session server-side.

## Role Enforcement Logic

The system enforces **Role-Based Access Control (RBAC)**:
- **Analyst**: Default role. Can view the dashboard, search profiles, and browse the explorer.
- **Admin**: Full access. Inherits all Analyst permissions and can additionally trigger profile creation and data exports.

Permissions are checked both at the UI level (hiding/showing buttons) and enforced strictly at the Backend API level for every request.

## Natural Language Parsing

The Profile Explorer utilizes the backend's natural language processing engine. Users can enter queries like *"young males from Nigeria"* or *"people from USA aged 20-30"*. The backend parses these into structured database filters using advanced pattern matching and NLP logic, ensuring accessible data discovery for non-technical users.

## CLI Interaction

While this repository hosts the Web Portal, the system is fully accessible via the **Insighta CLI**. The CLI and Web Portal share the same authentication backend and data sources.

**Common CLI Commands:**
- `insighta login`: Authenticate using GitHub.
- `insighta profiles list`: Browse the global database.
- `insighta profiles search "query"`: Perform natural language search.
- `insighta profiles export --format csv`: Export filtered data to CSV.

For more details, visit the [Insighta CLI Repository](https://github.com/HNG14-Intelligence-Query/cli).

## Technology Stack

- **Backend Logic**: [FastAPI](https://fastapi.tiangolo.com/)
- **Templating**: [Jinja2](https://palletsprojects.com/p/jinja/)
- **Asynchronous HTTP**: [httpx](https://www.python-httpx.org/)
- **Styling**: Vanilla CSS (Custom Glassmorphism Design System)
- **Icons & Fonts**: Google Fonts (Inter)

## Getting Started

### Prerequisites
- Python 3.10+
- A running instance of the [Insighta Backend](https://github.com/HNG14-Intelligence-Query/backend)
- GitHub OAuth App credentials

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/HNG14-Intelligence-Query/web-portal.git
   cd web-portal
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**:
   Create a `.env` file in the root directory:
   ```env
   INSIGHTA_BACKEND_URL=https://your-backend-api.com
   GITHUB_CLIENT_ID=your_github_client_id
   SESSION_SECRET=your_random_session_secret
   ```

### Running Locally

```bash
uvicorn app:app --port 3000 --reload
```
Access the portal at `http://localhost:3000`.

## Engineering Standards

- **Conventional Commits**: All changes follow the `feat(scope): description` or `fix(scope): description` format.
- **Modern UI**: Implements responsive design, glassmorphism effects, and micro-interactions for a premium user experience.
- **Robustness**: Defensive Jinja2 templating to handle API failures and missing data fields gracefully.
