"""One test-only success latch, then the genuine B6 CLI Worker entry."""
import argparse,sys
from CrashLatch import install_after_success_latch
p=argparse.ArgumentParser();p.add_argument('--data-dir',required=True);p.add_argument('--resource-manifest',required=True);p.add_argument('--target-run',required=True);p.add_argument('--latch-dir',required=True);a=p.parse_args()
install_after_success_latch('finish_output',a.latch_dir,a.target_run)
from video_creator.cli.main import main
sys.argv=['video_creator','worker','--data-dir',a.data_dir,'--workflow','gate0-local-render-v1','--resource-manifest',a.resource_manifest,'--run-id',a.target_run,'--max-seconds','70']
raise SystemExit(main())
