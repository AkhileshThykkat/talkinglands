# Talking Lands assessment submission : Akhilesh m t

### Setup

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    ```
2.  **Activate the virtual environment:**
    ```bash
    source .venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4. **Set DB URI in env**
export DB_URI="postgresql://user:password@host:port/database"

5.  **Run the application:**
    ```bash
    python3 app/main.py
### Running Tests

6.  **Run the tests:**
    ```bash
    pytest -v tests/main.py
   