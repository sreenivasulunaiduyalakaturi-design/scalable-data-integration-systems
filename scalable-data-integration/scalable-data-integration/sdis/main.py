import argparse
import logging
import os

from .pipeline import load_config, run_pipeline


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scalable Data Integration System")
    ap.add_argument("--config", default="config/pipeline.json")
    ap.add_argument("--workers", type=int, help="override worker count")
    ap.add_argument("--batch-size", type=int, help="override batch size")
    ap.add_argument("--executor", choices=["thread", "process"], help="override executor type")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(args.config)
    if args.workers:
        cfg["workers"] = args.workers
    if args.batch_size:
        cfg["batch_size"] = args.batch_size
    if args.executor:
        cfg["executor"] = args.executor
    os.makedirs(os.path.dirname(cfg["target"]["database"]) or ".", exist_ok=True)

    metrics = run_pipeline(cfg)
    print("\n=== Summary ===")
    for m in metrics:
        print(f"{m.dataset:<10} read={m.read:<7} loaded={m.loaded:<7} rejected={m.rejected:<5} "
              f"{m.seconds:.2f}s  sources={m.by_source}")


if __name__ == "__main__":
    main()
