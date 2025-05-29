from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
import httpx
import os
from typing import Dict, Any

app = FastAPI(title="YouTube Proxy Server", version="1.0.0")

# Configure httpx client with longer timeouts
client = httpx.AsyncClient(
    timeout=httpx.Timeout(60.0),
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
)

@app.get("/")
async def root():
    return {
        "message": "YouTube Proxy Server", 
        "status": "running",
        "note": "This proxy forwards requests to bypass IP blocking"
    }

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_request(request: Request, path: str):
    """Forward all requests through this proxy"""
    try:
        # Get the target URL from query parameter or reconstruct from path
        target_url = request.query_params.get('url')
        if not target_url:
            # If no URL provided, assume it's a YouTube URL
            if not path.startswith('http'):
                target_url = f"https://www.youtube.com/{path}"
            else:
                target_url = path
        
        # Get request headers (exclude host and other proxy-specific headers)
        headers = dict(request.headers)
        headers.pop('host', None)
        headers.pop('x-forwarded-for', None)
        headers.pop('x-forwarded-proto', None)
        
        # Add browser-like headers
        headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Get request body if present
        body = None
        if request.method in ['POST', 'PUT', 'PATCH']:
            body = await request.body()
        
        # Forward the request
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=dict(request.query_params) if not request.query_params.get('url') else None,
            follow_redirects=True
        )
        
        # Return the response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get('content-type')
        )
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Proxy request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

@app.on_event("startup")
async def startup():
    print("YouTube Proxy Server starting...")

@app.on_event("shutdown")
async def shutdown():
    await client.aclose()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 
