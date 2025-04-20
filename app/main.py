from fastapi import FastAPI
from fastapi.responses import ORJSONResponse, HTMLResponse

from routers import PointsRouter, PolygonRouter, GeoRouter

app = FastAPI(debug=True, default_response_class=ORJSONResponse)


app.include_router(router=PointsRouter)
app.include_router(router=PolygonRouter)
app.include_router(router=GeoRouter)


@app.get(
    "/",
    response_class=HTMLResponse,
    tags=[
        "Index Page",
    ],
)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Talking Lands Assessment</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet" />
    </head>
    <body class="bg-gradient-to-br from-green-100 to-blue-200 min-h-screen flex items-center justify-center">
        <div class="bg-white bg-opacity-90 rounded-xl shadow-lg p-10 max-w-lg w-full text-center">
            <h1 class="text-3xl font-bold text-green-700 mb-4">Talking Lands Assessment</h1>
            <p class="mb-6 text-gray-700">
                Visit the <a href="/docs" class="text-blue-500 underline hover:text-blue-700 font-medium">API documentation</a>.
            </p>
            <div class="mt-8 text-sm text-gray-500 space-y-1">
                <span class="block">
                    Submitted by <span class="font-semibold text-gray-700">Akhilesh m t</span>
                </span>
                <span class="block">
                    Email: <a href="mailto:akhileshthykkat843@gmail.com" class="text-blue-500 underline hover:text-blue-700">akhileshthykkat843@gmail.com</a>
                </span>
                <span class="block">
                    Phone: <a href="tel:+917994555175" class="text-blue-500 underline hover:text-blue-700">+91-7994555175</a>
                </span>
                <span class="block">
                    Submission date: <span class="font-mono text-gray-700">Sunday, April 20, 2025, 7:47 PM IST</span>
                </span>
            </div>
        </div>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", port=8080, host="0.0.0.0", reload=True)
