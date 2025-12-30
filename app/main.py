from datetime import datetime

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI(title="Pipeline", version="0.1.0")


def get_current_time() -> datetime:
    return datetime.now()


def get_greeting(name: str) -> str:
    if not name.strip():
        name = "anonymous"

    hour = get_current_time().hour

    if 6 <= hour < 12:
        return f"Good morning {name}"
    elif 12 <= hour < 18:
        return f"Good afternoon {name}"
    elif 18 <= hour < 22:
        return f"Good evening {name}"
    else:
        return f"Go to bed {name}"


@app.get("/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello, World"}


@app.get("/greet", response_class=HTMLResponse)
def greet_form() -> str:
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Greeting</title>
    </head>
    <body>
        <h1>Welcome</h1>
        <form method="post">
            <label for="name">Enter your name:</label>
            <input type="text" id="name" name="name">
            <button type="submit">Submit</button>
        </form>
    </body>
    </html>
    """


@app.post("/greet", response_class=HTMLResponse)
def greet_submit(name: str = Form("")) -> str:
    greeting = get_greeting(name)
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Greeting</title>
    </head>
    <body>
        <h1>{greeting}</h1>
        <a href="/greet">Try again</a>
    </body>
    </html>
    """
