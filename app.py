import os
import secrets
from fastapi import FastAPI, Request, HTTPException, Response, Depends, Form
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
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    access_token = request.cookies.get("access_token")
    if not access_token:
        return RedirectResponse("/login")
    return RedirectResponse("/dashboard")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # Embed the web portal's own token-receive URL inside state.
    # Format: web:<callback_url>:<nonce>
    # The backend will redirect back here with tokens in query params after OAuth.
    # This avoids registering localhost:3000 as a redirect_uri in GitHub — only the Vercel URL is needed.
    nonce = secrets.token_urlsafe(16)
    token_receive_url = str(request.url_for("receive_tokens"))
    state = f"web:{token_receive_url}:{nonce}"
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}&state={state}&scope=read:user%20user:email"
    )
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
