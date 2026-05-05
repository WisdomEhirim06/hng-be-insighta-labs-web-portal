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
    access_token = request.cookies.get("access_token")
    if not access_token:
        return RedirectResponse("/login")
    return RedirectResponse("/dashboard")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # The backend's /auth/github endpoint handles the full OAuth initiation.
    # It will generate a 'web:{nonce}' state and, after GitHub auth, redirect
    # tokens back to this portal's /auth/tokens endpoint via WEB_PORTAL_URL env var.
    github_auth_url = f"{BACKEND_URL}/auth/github"
    return templates.TemplateResponse(request=request, name="login.html", context={"github_auth_url": github_auth_url})

@app.get("/auth/tokens", name="receive_tokens")
async def receive_tokens(
    request: Request,
    access_token: str,
    refresh_token: str,
    username: str = "",
    role: str = "",
    state: str = "",
):
    """Receives tokens from the backend redirect and stores them in HTTP-only cookies."""
    response = RedirectResponse("/dashboard")
    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="lax")
    response.set_cookie(key="username", value=username, httponly=False, samesite="lax")
    response.set_cookie(key="role", value=role, httponly=False, samesite="lax")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token: return RedirectResponse("/login")
    
    username = request.cookies.get("username", "User")
    role = request.cookies.get("role", "analyst")

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND_URL}/api/profiles", headers={"X-API-Version": "1", "Authorization": f"Bearer {token}"})
        data = resp.json() if resp.status_code == 200 else {"total": 0, "data": []}
        
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"data": data, "username": username, "role": role})

@app.get("/profiles", response_class=HTMLResponse)
async def profiles_page(request: Request, q: str = None, page: int = 1, limit: int = 10):
    token = request.cookies.get("access_token")
    if not token: return RedirectResponse("/login")
    
    headers = {"X-API-Version": "1", "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        if q:
            resp = await client.get(f"{BACKEND_URL}/api/profiles/search?q={q}&page={page}&limit={limit}", headers=headers)
        else:
            resp = await client.get(f"{BACKEND_URL}/api/profiles?page={page}&limit={limit}", headers=headers)
        data = resp.json() if resp.status_code == 200 else {"data": [], "page": 1, "total_pages": 1}

    return templates.TemplateResponse(request=request, name="profiles.html", context={"data": data, "q": q})

@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("username")
    response.delete_cookie("role")
    return response
