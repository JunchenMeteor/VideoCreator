"""Own fixture only: no product import, CLI, FFmpeg, private instance or provider."""
import hashlib,json,os,sys,threading,time,unittest
from pathlib import Path
from types import SimpleNamespace
REPO=Path(__file__).resolve().parents[2];sys.path[:0]=[str(REPO/'tests/gate0'),str(REPO/'tests/gate0/T14Fixture'),str(REPO/'tools/testing')]
from t14_evidence import Journal
from SuccessLatch import wrap_after_success
from t14_resource_preflight import inspect_paths
ROOT=Path(os.environ['VIDEO_CREATOR_T14_SANITY']);ROOT.mkdir(parents=True,exist_ok=False)
class OwnFixtureSanity(unittest.TestCase):
 def test_journal_chain_and_reject_credential_data_before_write(self):
  journal=Journal(ROOT/'ObservationEvents','fixture_sanity');first,digest=journal.record('synthetic_fixture_start',{'synthetic_pid':123,'not_actual_creation':True});original=first.read_bytes();second,next_digest=journal.record('synthetic_fixture_end',{'actual_product_started':False});row=json.loads(second.read_text('utf8'));self.assertEqual(row['previous_event_sha256'],digest);self.assertEqual(first.read_bytes(),original);self.assertNotIn(b'\r\n',original);self.assertEqual(row['evidence_kind'],'fixture_sanity')
  with self.assertRaises(ValueError):journal.record('rejected',{'Authorization':'Bearer fake-fixture-text'})
  self.assertEqual(len(list(journal.root.glob('Event*.json'))),2)
 def test_success_return_barrier_and_original_failure_no_false_latch(self):
  calls=[];result=object();directory=ROOT/'SuccessLatch'
  def original(self,lease,reservation):calls.append((lease.run_id,reservation.step_key));return result
  wrapped=wrap_after_success(original,'finish_output',directory,'synthetic-run','synthetic-step','fixture_sanity');answers=[];thread=threading.Thread(target=lambda:answers.append(wrapped(None,SimpleNamespace(run_id='synthetic-run'),SimpleNamespace(step_key='synthetic-step'))));thread.start();deadline=time.monotonic()+2
  while not (directory/'LatchReady.json').exists():
   self.assertLess(time.monotonic(),deadline);time.sleep(.01)
  row=json.loads((directory/'LatchReady.json').read_text('utf8'));self.assertTrue(row['underlying_call_returned']);self.assertEqual(row['evidence_kind'],'fixture_sanity');self.assertEqual(len(calls),1);self.assertTrue(thread.is_alive());(directory/'ReleaseLatch').write_bytes(b'fixture-release');thread.join(timeout=2);self.assertFalse(thread.is_alive());self.assertIs(answers[0],result)
  def failure(*args):raise RuntimeError('Own fake callable failed')
  failed_folder=ROOT/'NeverLatch';failed=wrap_after_success(failure,'finish_output',failed_folder,'synthetic-run','synthetic-step','fixture_sanity')
  with self.assertRaises(RuntimeError):failed(None,SimpleNamespace(run_id='synthetic-run'),SimpleNamespace(step_key='synthetic-step'))
  self.assertFalse(failed_folder.exists())
 def test_explicit_resource_hash_on_own_text_only(self):
  sample=ROOT/'PlainFixture.txt';sample.write_bytes(b'Own fixture text only\n');items=inspect_paths([str(sample)]);self.assertEqual(items[0]['sha256'],hashlib.sha256(sample.read_bytes()).hexdigest());self.assertEqual(items[0]['bytes'],len(sample.read_bytes()))
  with self.assertRaises(ValueError):inspect_paths([])
  self.assertFalse(any(name.startswith('video_creator') for name in sys.modules))
if __name__=='__main__':unittest.main()
