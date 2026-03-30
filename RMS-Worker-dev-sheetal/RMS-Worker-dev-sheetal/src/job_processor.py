# Job Processor
import os
import sys
import json
import uuid
import signal
import asyncio
import multiprocessing
import redis.asyncio as redis 

from typing import Optional, Dict
from datetime import datetime 

from src.exceptions import PermanentJobFailureError
from src.data_class.job_processor_type import JobProcessorType
from src.data_class.job_processor_options import JobProcessorOptions 

MAX_RETRIES = 3 
LOCK_TIMEOUT_SECONDS = 300 
HEARTBEAT_TTL_SECONDS = 30 
HEARTBEAT_INTERVAL_SECONDS = 10 
STALE_LOCK_CHECK_INTERVAL_SECONDS = 30


class JobProcessor:
    def __init__(self, options: JobProcessorOptions):
        self.worker_id = str(uuid.uuid4())
        self.redis_pool = redis.ConnectionPool(
            host=options.redis_host,
            port=options.redis_port,
            db=options.redis_db,
            decode_responses=True
        )
        self.job_queue = options.job_queue
        self.worker_heartbeat = options.worker_heartbeat
        self.worker_set = options.worker_set
        self.active_jobs = set()
        self.should_exit = False
        self.max_parallel_jobs = multiprocessing.cpu_count()
        # NOTE: Keeping the executor property for structure but setting it to None
        self.executor = None 
        self.processors = options.processors

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        print(f"[INFO] JobProcessor initialized: worker_id={self.worker_id}")

    def get_redis(self):
        # NOTE: This now returns an async client due to the corrected import.
        return redis.Redis(connection_pool=self.redis_pool)

    def handle_shutdown(self, signum, frame):
        print("Shutdown signal received, cleaning up...")
        self.should_exit = True

    async def acquire_lock(self, redis_client, task_id, lock_timeout=300): # Changed default to 300
        """
        Acquire a distributed lock for the job using Redis
        Returns True if lock was acquired, False otherwise
        """
        lock_key = f"lock:{task_id}"
        lock_value = f"{self.worker_id}:{datetime.now().isoformat()}"

        # Try to acquire lock with SET NX (only set if not exists)
        acquired = await redis_client.set(
            lock_key,
            lock_value,
            nx=True,
            ex=lock_timeout
        )

        if acquired:
            print(f"Acquired lock for job {task_id}")
            return True
        return False

    async def release_lock(self, redis_client, task_id):
        """Release the distributed lock for the job"""
        lock_key = f"lock:{task_id}"
        # Only delete if we own the lock
        lock_value = await redis_client.get(lock_key)
        if lock_value and lock_value.startswith(self.worker_id):
            await redis_client.delete(lock_key)
            print(f"Released lock for job {task_id}")


    # ============================================================
    # ADDED EDGE CASE LOGIC (Retry Wrapper)
    # ============================================================

    async def process_job_with_retry_logic(self, task_id: str):
        """
        Wraps process_job to catch fatal exceptions and requeue with retry limit.
        Centralizes lock cleanup in a top-level finally block.
        """
        redis_client = self.get_redis()
        
        try:
            try:
                # Execute Core Processing Logic
                processed = await self.process_job(task_id)

                if processed:
                    print(f"[STATUS] Task {task_id} completed successfully")
                else:
                    print(f"[STATUS] Task {task_id} skipped (not processed)")
                return

            except Exception as e:
                # Handle System-Level Failures
                print(f"[ERROR] Task {task_id} failed with {type(e).__name__}: {str(e)}")

                try:
                    # Check Retry Count
                    job_key = f"job:{task_id}"
                    retry_count = await redis_client.hincrby(job_key, "retry_count", 1)
                    
                    print(f"[WARN] Task {task_id} retry attempt {retry_count}/{MAX_RETRIES}")

                    if retry_count > MAX_RETRIES:
                        # Permanent Failure - Exceeded Max Retries
                        print(f"[ERROR] Task {task_id} permanently failed after {retry_count} attempts")
                        
                        # Mark job as permanently failed
                        await redis_client.hset(
                            job_key,
                            mapping={
                                "status": "permanently_failed",
                                "retry_count": retry_count,
                                "final_error": f"{type(e).__name__}: {str(e)}",
                                "failed_at": datetime.now().isoformat()
                            }
                        )
                        
                        # Move to dead letter queue (FIFO)
                        dead_letter_queue = f"{self.job_queue}:dead_letter"
                        await redis_client.rpush(dead_letter_queue, task_id)
                        
                        print(f"[ERROR] Moved task {task_id} to dead letter queue")
                        return

                    # Requeue with FIFO Policy
                    await redis_client.rpush(self.job_queue, task_id)
                    
                    print(f"[STATUS] Task {task_id} requeued for retry {retry_count}/{MAX_RETRIES}")
                    
                    # Update job metadata
                    await redis_client.hset(
                        job_key,
                        mapping={
                            "status": "retry_pending",
                            "last_error": f"{type(e).__name__}: {str(e)}",
                            "last_retry_at": datetime.now().isoformat()
                        }
                    )
                
                except Exception as requeue_error:
                    print(f"[CRIT] Failed to requeue task {task_id}: {requeue_error}")
                
                return

        except Exception as outer_e:
            print(f"[CRIT] Fatal error in retry wrapper for {task_id}: {outer_e}")
        
        finally:
            # FINAL LOCK CLEANUP (Guaranteed to run)
            # Clean up active_jobs set and release the lock.
            self.active_jobs.discard(task_id)
            try:
                await self.release_lock(redis_client, task_id)
            except Exception as lock_error:
                print(f"[WARN] Lock release failed for {task_id}: {lock_error}")
            
            await redis_client.close() # Close Redis connection


    async def process_job(self, task_id):
        """Process a single job"""
        redis_client = self.get_redis()

        # Try to acquire lock for the job
        if not await self.acquire_lock(redis_client, task_id):
            print(f"Could not acquire lock for job {task_id}, skipping...")
            return False

        try:
            # NOTE: All synchronous redis calls here must now be awaited
            job = await redis_client.hgetall(f"job:{task_id}")
            if not job:
                print(f"Job {task_id} not found, skipping...")
                return False
            
            # Validate process_type key existence (Edge case)
            if "process_type" not in job:
                print(f"Job {task_id} missing 'process_type', skipping...")
                return False
            
            processor_type = job["process_type"]
            print("===============process_type :",processor_type)
            if not processor_type:
                print(f"Job {task_id} does not have a processor_type, skipping...")
                return False
            
            processor = self.processors.get(JobProcessorType(processor_type), "")
            print("=============processor :",processor_type) 

            if not processor:
                raise Exception(f"Not implemented :{processor_type}")
            await processor.invoke(job)
            return True
          
        except Exception as e:
            # Re-raise to trigger the retry/failure logic in the wrapper.
            raise 

        finally:
            # Removed cleanup handled by process_job_with_retry_logic
            pass 


    async def heartbeat(self):
        """Send periodic heartbeat to Redis"""
        redis_client = self.get_redis()
        while not self.should_exit:
            await redis_client.sadd(self.worker_set, self.worker_id)
            await redis_client.setex(
                f"worker_heartbeat:{self.worker_id}",
                30,  # TTL in seconds
                datetime.now().isoformat()
            )
            await asyncio.sleep(10)  # Heartbeat every 10 seconds

    async def check_and_recover_stale_locks(self):
        """Check for stale locks and recover jobs if needed"""
        redis_client = self.get_redis()
        while not self.should_exit:
            try:
                # Get all locks
                lock_keys = await redis_client.keys("lock:*")
                for lock_key in lock_keys:
                    # Ensure lock_key is decoded before splitting
                    lock_key = lock_key.decode() if isinstance(lock_key, bytes) else lock_key
                    task_id = lock_key.split(":")[1]
                    lock_value = await redis_client.get(lock_key)

                    if lock_value:
                        lock_value = lock_value.decode() if isinstance(lock_value, bytes) else lock_value
                        worker_id = lock_value.split(":")[0]
                        # Check if worker is still alive
                        if not await redis_client.exists(f"worker_heartbeat:{worker_id}"):
                            print(f"[WARN] Recovering stale lock for task {task_id}")
                            # Remove stale lock
                            await redis_client.delete(lock_key)
                            # Return job to queue
                            await redis_client.lpush(self.job_queue, task_id)
            except Exception as e:
                print(f"[ERROR] Error checking stale locks: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds
            
    # Renamed main loop to process_job_queue (old was run)
    async def run(self):
        redis_client = self.get_redis()
        print(f"Worker {self.worker_id} started, processing up to {self.max_parallel_jobs} jobs in parallel...")

        # Start heartbeat and stale lock checker
        asyncio.create_task(self.heartbeat())
        asyncio.create_task(self.check_and_recover_stale_locks())

        while not self.should_exit:
            try:
                # Check if we can process more jobs
                if len(self.active_jobs) < self.max_parallel_jobs:
                    # Use blpop (blocking pop) for better latency and efficiency
                    result = await redis_client.blpop(self.job_queue, timeout=1) 
                    
                    if result:
                        _, task_id = result
                        # Handle potential byte response from blpop
                        task_id = task_id.decode() if isinstance(task_id, bytes) else task_id
                        
                        self.active_jobs.add(task_id)
                        # Pass job to the retry wrapper
                        asyncio.create_task(self.process_job_with_retry_logic(task_id))

                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"[ERROR] Error in main loop: {e}")
                await asyncio.sleep(1)

        # Cleanup on shutdown
        await redis_client.srem(self.worker_set, self.worker_id)
        await redis_client.delete(f"worker_heartbeat:{self.worker_id}")

        # Return unfinished jobs to queue
        for task_id in self.active_jobs:
            await redis_client.lpush(self.job_queue, task_id)

        await redis_client.close()