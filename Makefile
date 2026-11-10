install:; pip install -r requirements.txt
run:; streamlit run src/app.py
eval:; python eval/run_eval.py
test:; pytest -q
