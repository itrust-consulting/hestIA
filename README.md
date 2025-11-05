- Download and install ollama for windows from https://ollama.com/download/windows
- check that ollama is installed (PowerShell ollama --version)
- Use Powershell to start ollama service with >ollama serve
- open new powershell and pull LLM > ollama llama3.1:8b
- navigate to project folder
- activate python venv (.wenv) > .\wenv\Scripts\Activate.ps1
- before starting the benchmark run a random query to initialize the model
```console
foo@bar:~$ curl.exe http://127.0.0.1:11434/api/generate -H "Content-Type: application/json" -d "@init_prompt.json"
```

- run the benchmark script with > python.exe .\benchmark.py

- Please verify that if your system does automatically use the GPU (see taskmanager) the benchmark script does also correctly capture your gpu info.
- Potentially setup something similar to monitor_resource for GPU usage (only if can be quickly implemented)

Notes:
- .venv is the venv for linux env
- Use windows env as it seems that linux is slower (only tested with WSL though)
- also start ollama server on same system, i.e., either wsl or windows. Otherwise, there seems to be some routing issues or something.


To run main.py and langChain.py pull the model "mxbai-embed-large" with > ollama pull mxbai-embed-large

This model is used to transform strings into vector embeddings. 
langchain.py just a quick test of their pdf reader. Can only retrieve text but all structure is lost. Rather use own preprocessing or better pdfreader that allows further processing. 

Quick start:
```console
foo@bar:~$ ollama serve
foo@bar:~$ docker run -p 6333:6333 -p 6334:6334 -v "$(pwd)/qdrant_storage:/qdrant/storage:z" qdrant/qdrant
```

Check if qdrant Db is initialized: http://localhost:6333/dashboard#/collections
should see PoC-Datastore + PoC-Datastore-1

Otherwise initialize vector DB:
```console
foo@bar:~$ python .\rag.py
foo@bar:~$ Invoke-RestMethod -Uri http://localhost:8099/init ` 
-Method POST `
-Headers @{ "Content-Type" = "application/json" } `
-Body '{"dirpath": "./docs", "collection": "PoC-Datastore"}'
```
or in bash
```console
foo@bar:~$ curl -X POST http://localhost:8099/init -H "Content-Type: application/json"  -d '{"prompt":"Explain secure boot"}'
```

Start web app with
```console
foo@bar:~$ python .\view.py
```
Acces via http://127.0.0.1:7860/

Model and Collection are hardcoded selections for now.