#!/usr/bin/env python3
"""Copy old public trace LF frames; no UE, worker, solver or private input IO."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
from universe_iteration import native_replay


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=Path,default=Path(__file__).with_name('old3-catalog.json'))
    for name in ('run-id','product-source-sha','tool-source-sha','output-dir'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    catalog=json.loads(args.catalog.read_bytes())
    if catalog['format']!='universe-i15-old3-catalog.v1':
        parser.error('unsupported catalog')
    result=native_replay.prepare_replay_cases(run_id=args.run_id,product_source_sha=args.product_source_sha,
        tool_source_sha=args.tool_source_sha,selections=catalog['selections'],allowed_sources=catalog['allowed_sources'],
        public_paths=catalog['public_paths'],output_dir=args.output_dir)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
