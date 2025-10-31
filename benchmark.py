import requests
import json
import csv
import os
import time
import psutil
import platform
import subprocess
import threading
import argparse
from datetime import datetime



def write_hardware_info(f, hardware_info):
    """
    Write hardware metadata at the top of the CSV file
    in a readable key-value format, as commented lines.
    """
    f.write("# Hardware information:\n")
    
    # CPU info
    cpu_info = hardware_info.get("cpu", {})
    for k, v in cpu_info.items():
        f.write(f"# CPU {k}: {v}\n")
    
    # GPU info (may be empty)
    gpus = hardware_info.get("gpu", [])
    if gpus:
        for i, gpu in enumerate(gpus):
            f.write(f"# GPU {i+1}:\n")
            for k, v in gpu.items():
                f.write(f"#   {k}: {v}\n")
    else:
        f.write("# GPU: None (CPU-only)\n")
    
    f.write("\n")

def get_system_info():
    info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "cpu_model": platform.processor(),
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
        "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2)
    }
    return info
    
def get_gpu_info():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True, text=True
        )
        gpus = []
        for line in result.stdout.strip().splitlines():
            name, mem, driver = [x.strip() for x in line.split(",")]
            gpus.append({
                "name": name,
                "memory_mb": int(mem),
                "driver_version": driver
            })
        return gpus
    except FileNotFoundError:
        return []  # No NVIDIA GPU

    
hardware_info = {
    "cpu": get_system_info(),
    "gpu": get_gpu_info()
}


def get_perf_json(time, model, prompt, response, tokens, latency_sec, tokens_per_sec, avg_cpu, peak_mem):

    json_obj = {
        "timestamp": str(time),
        "model": model,
        "prompt": prompt,
        "response": response,
        "tokens": int(tokens),
        "latency_sec": round(latency_sec, 3),
        "tokens_per_sec": round(tokens_per_sec, 2),
        "avg_cpu_percent": round(avg_cpu, 1),
        "peak_memory_mb": round(peak_mem, 1),
    }
    return json_obj
    
def monitor_resources(stop_flag, interval=0.1):
    """
    Continuously record total CPU% and RSS memory used by Ollama and its child processes.
    Returns a list of (timestamp, total_cpu_percent, total_mem_mb).
    """
    samples = []

    # Build persistent map of ollama-related processes
    tracked = {}
    for p in psutil.process_iter(['pid', 'name']):
        if 'ollama' in p.info['name'].lower():
            try:
                proc = psutil.Process(p.info['pid'])
                tracked[p.info['pid']] = proc
                for child in proc.children(recursive=True):
                    tracked[child.pid] = child
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    # Prime all processes (first call always returns 0)
    for proc in tracked.values():
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sampling loop
    while not stop_flag.is_set():
        total_cpu = 0.0
        total_mem = 0.0

        # Update tracked processes
        for pid, proc in list(tracked.items()):
            try:
                total_cpu += proc.cpu_percent(interval=None)
                total_mem += proc.memory_info().rss / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                tracked.pop(pid, None)

        # Detect new children that may have spawned since start
        for p in psutil.process_iter(['pid', 'name']):
            if 'ollama' in p.info['name'].lower() and p.info['pid'] not in tracked:
                try:
                    proc = psutil.Process(p.info['pid'])
                    tracked[p.info['pid']] = proc
                    proc.cpu_percent(interval=None)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        samples.append((time.time(), total_cpu, total_mem))
        time.sleep(interval)

    return samples


def run_prompt_request(model, prompt, url="http://localhost:11434/api/generate", stream=False):

    cheaders = {"Content-Type":"application/json"}
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        }

    stop_flag = threading.Event()
    samples = []
    thread = threading.Thread(
        target=lambda: samples.extend(monitor_resources(stop_flag)))
    thread.start()

    timestamp = datetime.now()
    t0 = time.perf_counter()
    try:
        response = requests.post(url, json=payload, headers=cheaders, timeout=(20, None))
    finally:
        stop_flag.set()
        thread.join()
    t1 = time.perf_counter()

    if response.status_code != 200:
        raise RuntimeError(f"Ollama returned {response.status_code}: {response.text}")

    data = response.json()
    text = data.get("response", "")
    
    
    tokens = len(text.split())

    latency = t1 - t0
    tokens_per_sec = tokens / latency if latency > 0 else 0

    avg_cpu = sum(s[1] for s in samples) / len(samples)
    # normalize 
    avg_cpu_system = avg_cpu / psutil.cpu_count(logical=True)

    peak_mem = max(s[2] for s in samples) if samples else 0

    
    perf = get_perf_json(timestamp, model, prompt, text, tokens, latency, tokens_per_sec, avg_cpu_system, peak_mem)
    
    return perf
    
    

def benchmark(models, prompts, output_file):
    """Benchmark models/prompts and write results as JSONL."""
    
    with open(output_file, "a+") as f:
        # write hardware metadata first
        write_hardware_info(f, hardware_info)
        
        for model in models:
            for prompt in prompts:
                print(f"→ Running benchmark for model='{model}' prompt='{prompt}'")
                try:
                    result = run_prompt_request(model, prompt)
                    f.write(json.dumps(result)+ "\n")
                    print(f"   {result['tokens']} tokens in {result['latency_sec']}s "
                          f"({result['tokens_per_sec']} tok/s, CPU {result['avg_cpu_percent']}%, "
                          f"Mem {result['peak_memory_mb']} MB)")
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")


if __name__ == "__main__":

    #parser = argparse.ArgumentParser(description="Benchmark local Ollama LLM performance.")
    #parser.add_argument("--models", nargs="+", required=True,
    #                    help="List of model names (e.g., llama3.2, mistral, codellama).")
    #parser.add_argument("--prompts", nargs="+", required=True,
    #                    help="List of text prompts to test.")
    #parser.add_argument("--output", default="benchmark_results.md",
    #                    help="Output CSV file path.")
    #args = parser.parse_args()

    models = ["llama3.1:8b"]
    prompts = [
           "Hi", 
           "How are you?",
           "What is the average of [8,5,7,7,9,11,3]",
           "How do we humans perceive color?"]

    output = "./benchmark_results.md"
    print(f"Starting benchmark")# on {len(args.models)} model(s), using {len(args.prompts)} prompts\n")
    #benchmark(args.models, args.prompts, args.output)
    benchmark(models, prompts, output)
    
    print(f"\n Benchmark completed. Results saved to {output}")