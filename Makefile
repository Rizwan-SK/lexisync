install:; pip install -r requirements.txt
run:; python -m streamlit run src/app.py --server.fileWatcherType none
eval:; python eval/run_eval.py data_core
test:; python -m pytest -q
