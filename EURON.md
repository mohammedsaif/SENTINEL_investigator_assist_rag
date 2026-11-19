# sentinel-explain

<!-- Written by Euron Code project setup. Run /init to let the model fill in the details. -->

Stack: Python, FastAPI, pytest

## Commands
- `pip install -r requirements.txt`
- `python -m pytest`

## Layout
```
app/  (12 files)
  __init__.py
  config.py
  explain.py
  llm.py
  main.py
  reason_codes.py
  rules.yaml
  schemas.py
  stores/
eval/  (1 files)
results/  (0 files)
scripts/  (4 files)
tests/  (2 files)
README.md
requirements.txt
```

Entry points: app/main.py

## Conventions
- (add the conventions of this project here)
- # Evaluation

### 1. Ten test transactions (5 fraud + 5 genuine, validation split)

```bash
python -m scripts.run_test_transactions                  # picks from rows where split = 'val'
# or: python -m scripts.run_test_transactions --ids-csv eval/val_ids.csv   (columns: transaction_id,is_fraud)
```

The script calls the running API and saves each response to `results/explain/<id>.json`, with a summary in `results/test_run_summary.md`.

<!-- paste results/test_run_summary.md here after running -->

### 2. Retrieval hit@5

`eval/retrieval_questions.json` holds 10 questions, each labelled with the document that contains the answer. To check the labels against your real document IDs:

```bash
python -m scripts.list_policy_docs     # shows every doc_id in the collection
python -m scripts.eval_retrieval       # writes results/retrieval_eval.md
```

A question counts as a hit if any of its top-5 chunks comes from the expected document (exact match or substring match). The script also reports MRR, which shows how high the correct document ranks.

<!-- paste results/retrieval_eval.md here after running -->

## Repo layout

```
app/
  main.py            FastAPI app, POST /explain, GET /health
  explain.py         orchestrator: fetch → rules → retrieve → LLM → ground
  rules.yaml         reason-code rules (edit field names to match your features)
  reason_codes.py    rule engine
  llm.py             prompt, Gemini structured output, citation grounding
  schemas.py         request / response models
  config.py          settings from .env
  stores/
    transactions.py  Supabase + MongoDB backends
    graph.py         Neo4j neighbourhood Cypher
    policy.py        Qdrant + Gemini Embedding 2 retrieval
scripts/             run_test_transactions, eval_retrieval, list_policy_docs
eval/                retrieval_questions.json
results/             saved /explain responses and eval reports
tests/               offline pipeline tests
```
