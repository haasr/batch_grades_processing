from concurrent import futures
from typing import Any, Callable, List

class RoundRobinWorkerPool:
    def __init__(self, items: List[Any], func: Callable[[Any], Any], num_workers: int = 3):
        """
        items: List of items to process.
        func: Function to apply to each item.
        num_workers: Number of concurrent workers.
        """
        self.items = items
        self.func = func
        self.num_workers = num_workers

    def _distribute_items_round_robin(self) -> List[List[Any]]:
        """Distribute items into buckets in a round-robin fashion."""
        buckets = [[] for _ in range(self.num_workers)]
        for idx, item in enumerate(self.items):
            buckets[idx % self.num_workers].append(item)
        return buckets

    def _worker(self, bucket: List[Any]) -> List[Any]:
        """Process each item in the bucket sequentially."""
        return [self.func(item) for item in bucket]

    def run(self) -> List[Any]:
        """Execute the processing in parallel using ThreadPoolExecutor."""
        all_results = []
        buckets = self._distribute_items_round_robin()

        with futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            jobs = [executor.submit(self._worker, bucket) for bucket in buckets]
            for job in futures.as_completed(jobs):
                all_results.extend(job.result())

        return all_results

class ChunkedWorkerPool:
    def __init__(self, items: List[Any], func: Callable[[List[Any]], Any], func_args: tuple=(), num_workers: int = 3):
        """
        items: List of items to process.
        func: Function that accepts a LIST of items and processes them.
        num_workers: Number of concurrent workers.
        """
        self.items = items
        self.func_args = func_args
        self.func = func
        self.num_workers = num_workers

    def _distribute_items_chunked(self) -> List[List[Any]]:
        """Distribute items into roughly equal-sized chunks."""
        total_items = len(self.items)
        base_chunk_size = total_items // self.num_workers
        remainder = total_items % self.num_workers

        chunks = []
        start_idx = 0

        for worker_idx in range(self.num_workers):
            # First 'remainder' workers get an extra item
            chunk_size = base_chunk_size + (1 if worker_idx < remainder else 0)
            end_idx = start_idx + chunk_size
            chunks.append(self.items[start_idx:end_idx])
            start_idx = end_idx

        return chunks

    def _worker(self, chunk: List[Any]) -> Any:
        """Process the entire chunk by calling func once."""
        return self.func(*(chunk, *self.func_args)) # Adding function arguments if there were any

    def run(self) -> List[Any]:
        """Execute the processing in parallel using ThreadPoolExecutor."""
        chunks = self._distribute_items_chunked()

        with futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            jobs = [executor.submit(self._worker, chunk) for chunk in chunks]
            results = [job.result() for job in jobs]

        return results