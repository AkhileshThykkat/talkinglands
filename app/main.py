from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

app = FastAPI(debug=True, default_response_class=ORJSONResponse)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", port=8080, host="0.0.0.0", reload=True)
