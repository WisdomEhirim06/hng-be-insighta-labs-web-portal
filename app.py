import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Insighta Labs+ Web Portal")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "web-secret-key"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

BACKEND_URL = os.getenv("INSIGHTA_BACKEND_URL", "https://hng14-be-intelligence-query.vercel.app")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not request.cookies.get("access_token"):
        return RedirectResponse("/login")
    return RedirectResponse("/dashboard")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # Redirect to the backend's /auth/github which initiates GitHub OAuth.
    # The backend's registered callback URL handles the rest and redirects
    # tokens back to /auth/tokens on this portal.
    github_auth_url = f"{BACKEND_URL}/auth/github"
    return templates.TemplateResponse(
        request=request, name="login.html", context={"github_auth_url": github_auth_url}
    )


@app.get("/auth/tokens")
async def receive_tokens(
    request: Request,
    access_token: str,
    refresh_token: str,
    username: str = "",
    role: str = "",
):
    """Called by the backend after GitHub OAuth completes.

    Stores tokens in HTTP-only cookies and sends the user to the dashboard.
    """
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", secure=True)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", secure=True)
    response.set_cookie("username", username, samesite="lax")
    response.set_cookie("role", role, samesite="lax")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    username = request.cookies.get("username", "User")
    role = request.cookies.get("role", "analyst")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BACKEND_URL}/api/profiles",
            headers={"X-API-Version": "1", "Authorization": f"Bearer {token}"},
        )
        data = resp.json() if resp.status_code == 200 else {"total": 0, "data": []}

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"data": data, "username": username, "role": role},
    )


@app.get("/profiles", response_class=HTMLResponse)
async def profiles_page(request: Request, q: str = None, page: int = 1, limit: int = 10):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    headers = {"X-API-Version": "1", "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        if q:
            resp = await client.get(
                f"{BACKEND_URL}/api/profiles/search?q={q}&page={page}&limit={limit}",
                headers=headers,
            )
        else:
            resp = await client.get(
                f"{BACKEND_URL}/api/profiles?page={page}&limit={limit}",
                headers=headers,
            )
        data = resp.json() if resp.status_code == 200 else {"data": [], "page": 1, "total_pages": 1}

    return templates.TemplateResponse(
        request=request, name="profiles.html", context={"data": data, "q": q}
    )


@app.get("/logout")
async def logout(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BACKEND_URL}/auth/logout",
                json={"refresh_token": refresh_token},
            )

    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("username")
    response.delete_cookie("role")
    return response
