# 1. Repo clone / folder me jaao
git clone <your-repo-url> && cd <repo>

# 2. Virtual env (recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Run
streamlit run app.py
