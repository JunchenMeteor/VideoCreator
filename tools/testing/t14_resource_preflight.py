"""Read-only exact declared runtime hashing; no product import or decoder execution."""
import argparse,hashlib,json
from datetime import UTC,datetime
from pathlib import Path

def inspect_paths(paths):
 result=[]
 if not isinstance(paths,list) or not paths or len(paths)>64:raise ValueError('Finite explicit resource list required')
 for text in paths:
  path=Path(text)
  if not path.is_absolute() or not path.is_file():raise ValueError('Missing absolute runtime resource')
  if any(part.lower() in {'.ssh','validationinstance'} for part in path.parts):raise ValueError('Private resource prohibited')
  result.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
 return result

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--runtime-inputs',required=True);parser.add_argument('--approved-source-freeze',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
 if not Path(args.approved_source_freeze).is_file():raise ValueError('Await approved final-source input before actual preflight')
 output=Path(args.output)
 if not output.is_absolute() or 'TestDevelopment' not in output.parts:raise ValueError('Own evidence directory required')
 if output.exists():raise ValueError('Never overwrite raw preflight')
 paths=json.loads(Path(args.runtime_inputs).read_text('utf8'))['paths'];records=inspect_paths(paths);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes((json.dumps({'observed_at':datetime.now(UTC).isoformat(),'scope':'Hash only, no decoder or product execution','runtime_inputs':records},ensure_ascii=False,indent=2)+'\n').encode('utf8'))
if __name__=='__main__':main()
