"""Prepared launcher for the genuine fixed CLI; not invoked during preparation."""
import argparse,sys
from pathlib import Path
from SuccessLatch import install_after_success_latch

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--data-dir',required=True);parser.add_argument('--resource-manifest',required=True);parser.add_argument('--target-run',required=True);parser.add_argument('--target-step',default='local-shot-1');parser.add_argument('--latch-dir',required=True);parser.add_argument('--approved-source-freeze',required=True);args=parser.parse_args()
 if not Path(args.approved_source_freeze).is_file():raise ValueError('No approved fixed-source input; never run WIP')
 install_after_success_latch('finish_output',args.latch_dir,args.target_run,args.target_step)
 from video_creator.cli.main import main as product_main
 sys.argv=['video_creator','worker','--data-dir',args.data_dir,'--workflow','gate0-local-render-v1','--resource-manifest',args.resource_manifest,'--run-id',args.target_run,'--max-seconds','70']
 return product_main()
if __name__=='__main__':raise SystemExit(main())
